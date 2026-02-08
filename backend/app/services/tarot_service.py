from typing import Dict, Any, Optional, Tuple
import random
from datetime import date
from ..core.db import supabase


class TarotService:
    def __init__(self):
        self.supabase = supabase
        self._card_count = self._get_total_card_count()

    def _get_total_card_count(self) -> int:
        """从数据库获取塔罗牌的总数"""
        response = self.supabase.table('tarot_cards').select(
            'id', count='exact'
        ).execute()
        return response.count if response.count is not None else 0

    def draw_daily_card(
        self, user_id: str, for_date: date, language: str = "zh-CN"
    ) -> Dict[str, Any]:
        """用户触发抽牌：先查存档，没有则真随机抽取并入库。"""
        import logging

        card_count = self._ensure_card_count()
        if card_count == 0:
            return {"error": "塔罗牌数据未初始化"}

        existing_record = self._get_draw_record(user_id, for_date)
        if existing_record:
            logging.info(
                f"📅 User {user_id} already drew on {for_date}, returning stored card."
            )
            card_id = existing_record.get('card_id')
            orientation = existing_record.get('orientation', 'upright')
            is_new_draw = False
        else:
            logging.info(f"🎲 User {user_id} drawing first card for {for_date} (real random)")
            card_id, orientation, is_new_draw = self._draw_and_save(
                user_id, for_date, card_count
            )

        if not card_id:
            logging.error("❌ 抽取塔罗牌失败或未能写入记录")
            return {"error": "抽取塔罗牌失败，请稍后重试"}

        result = self._build_card_response(card_id, orientation, language)
        result["is_new_draw"] = is_new_draw
        return result

    def get_card_by_id(
        self,
        card_id: int,
        orientation: str,
        language: str = "zh-CN",
        *,
        user_id: Optional[str] = None,
        draw_date: Optional[date] = None,
        persist: bool = False
    ) -> Dict[str, Any]:
        """根据卡片ID和朝向获取塔罗牌数据；可选地写入抽牌记录（用于前端抽卡模式）。"""
        import logging

        if persist and user_id and draw_date:
            self._ensure_draw_record(user_id, draw_date, card_id, orientation)

        try:
            result = self._build_card_response(card_id, orientation, language)
            logging.info(f"✅ Retrieved card {card_id} with orientation {orientation}")
            return result
        except Exception as e:
            logging.error(f"❌ Failed to get card by id {card_id}: {e}", exc_info=True)
            return {"error": f"获取塔罗牌失败: {str(e)}"}

    def get_all_cards(self, language: str = "zh-CN") -> list:
        """获取所有塔罗牌数据（用于前端抽卡）"""
        import logging
        try:
            response = self.supabase.table('tarot_cards').select('*').execute()
            cards = response.data

            # 如果需要翻译，处理每张卡片
            if language != "en" and language != "en-US":
                translated_cards = []
                for card in cards:
                    # 保存原始英文名称
                    original_card_name = card.get('card_name', '')

                    translations = card.get('translations', {})
                    if translations and language in translations:
                        trans = translations[language]
                        card_data = {
                            **card,
                            'card_name': trans.get('card_name', card.get('card_name')),
                            'card_name_en': original_card_name,  # 保留英文名称用于图片加载
                            'meaning_up': trans.get('meaning_up', card.get('meaning_up')),
                            'meaning_down': trans.get('meaning_down', card.get('meaning_down')),
                            'description': trans.get('description', card.get('description'))
                        }
                        rating_slug = self._generate_rating_slug(card_data)
                        if rating_slug:
                            card_data['card_id'] = rating_slug
                        translated_cards.append(card_data)
                    else:
                        # 如果没有翻译，也添加 card_name_en 字段
                        card_with_en = {**card, 'card_name_en': original_card_name}
                        rating_slug = self._generate_rating_slug(card_with_en)
                        if rating_slug:
                            card_with_en['card_id'] = rating_slug
                        translated_cards.append(card_with_en)
                cards = translated_cards
            else:
                # 英文语言也添加 card_name_en 字段（与 card_name 相同）
                cards_with_slug = []
                for card in cards:
                    card_with_en = {**card, 'card_name_en': card.get('card_name', '')}
                    rating_slug = self._generate_rating_slug(card_with_en)
                    if rating_slug:
                        card_with_en['card_id'] = rating_slug
                    cards_with_slug.append(card_with_en)
                cards = cards_with_slug

            logging.info(f"✅ Retrieved {len(cards)} tarot cards for language: {language}")
            return cards
        except Exception as e:
            logging.error(f"❌ Failed to get all tarot cards: {e}", exc_info=True)
            return []

    def _ensure_card_count(self) -> int:
        """确保卡牌总数可用"""
        import logging
        if self._card_count == 0:
            self._card_count = self._get_total_card_count()
            logging.info(f"🔄 Refreshed tarot card count: {self._card_count}")
        return self._card_count

    def _get_draw_record(self, user_id: str, for_date: date) -> Optional[Dict[str, Any]]:
        """查询用户指定日期的抽牌记录"""
        import logging
        try:
            response = self.supabase.table('user_daily_draws').select('*').eq(
                'user_id', user_id
            ).eq('draw_date', for_date.isoformat()).limit(1).execute()
            records = response.data or []
            return records[0] if len(records) > 0 else None
        except Exception as e:
            logging.error(f"❌ Failed to query draw record for {user_id} on {for_date}: {e}", exc_info=True)
            return None

    def _draw_and_save(
        self, user_id: str, for_date: date, card_count: int
    ) -> Tuple[Optional[int], Optional[str], bool]:
        """真随机抽牌并尝试存储，返回 (card_id, orientation, is_new_draw)。"""
        import logging

        rng = random.SystemRandom()
        card_id = rng.randint(1, card_count)
        orientation = "upright" if rng.random() > 0.5 else "reversed"

        record, is_new = self._save_user_draw(
            user_id=user_id,
            card_id=card_id,
            orientation=orientation,
            for_date=for_date
        )
        if record:
            return record.get('card_id', card_id), record.get('orientation', orientation), is_new

        existing = self._get_draw_record(user_id, for_date)
        if existing:
            logging.info("ℹ️ Falling back to existing draw record after save failure")
            return existing.get('card_id'), existing.get('orientation', 'upright'), False

        return None, None, False

    def _ensure_draw_record(
        self, user_id: str, for_date: date, card_id: int, orientation: str
    ) -> Tuple[Optional[int], Optional[str]]:
        """确保存在当天抽牌记录（前端抽卡场景用）。"""
        import logging

        existing = self._get_draw_record(user_id, for_date)
        if existing:
            return existing.get('card_id'), existing.get('orientation', 'upright')

        record, _ = self._save_user_draw(
            user_id=user_id,
            card_id=card_id,
            orientation=orientation,
            for_date=for_date
        )
        if record:
            logging.info(f"📝 Saved manual draw for user {user_id} on {for_date}")
            return record.get('card_id'), record.get('orientation', orientation)

        logging.warning(f"⚠️ Could not persist manual draw for user {user_id} on {for_date}")
        return card_id, orientation

    def _save_user_draw(
        self, user_id: str, card_id: int, orientation: str, for_date: date
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """写入抽牌记录；如遇唯一冲突则返回已存在的记录。"""
        import logging

        try:
            response = self.supabase.table('user_daily_draws').insert({
                "user_id": user_id,
                "card_id": card_id,
                "orientation": orientation,
                "draw_date": for_date.isoformat()
            }).execute()

            if getattr(response, 'data', None):
                record = response.data[0] if isinstance(response.data, list) else response.data
                return record, True

            # Supabase 会在重复插入时返回 error 信息
            error_message = str(getattr(response, 'error', ''))
            if error_message:
                logging.warning(f"⚠️ Insert draw record error: {error_message}")
                if "duplicate" in error_message.lower() or "unique" in error_message.lower():
                    existing = self._get_draw_record(user_id, for_date)
                    if existing:
                        return existing, False

        except Exception as e:
            logging.error(f"❌ Failed to save draw record: {e}", exc_info=True)
            existing = self._get_draw_record(user_id, for_date)
            if existing:
                return existing, False

        return None, False

    def _build_card_response(self, card_id: int, orientation: str, language: str) -> Dict[str, Any]:
        """获取卡牌详情并生成前端所需字段。"""
        import logging

        response = self.supabase.table('tarot_cards').select(
            '*'
        ).eq('id', card_id).single().execute()

        card_data = response.data
        if not card_data:
            logging.error(f"❌ 未找到ID为 {card_id} 的塔罗牌")
            return {"error": f"未找到ID为 {card_id} 的塔罗牌"}

        logging.info(f"🔍 Original card_data keys: {list(card_data.keys())}")
        logging.info(f"🔍 Original card_name: '{card_data.get('card_name')}'")

        original_card_name = card_data.get('card_name', '')
        card_payload = {**card_data}

        if language != "en" and language != "en-US":
            translations = card_payload.get('translations', {})
            if translations and language in translations:
                trans = translations[language]
                card_payload = {
                    **card_payload,
                    'card_name': trans.get(
                        'card_name', card_payload.get('card_name')
                    ),
                    'meaning_up': trans.get(
                        'meaning_up', card_payload.get('meaning_up')
                    ),
                    'meaning_down': trans.get(
                        'meaning_down', card_payload.get('meaning_down')
                    ),
                    'description': trans.get(
                        'description', card_payload.get('description')
                    )
                }
                logging.info(f"🔍 Translated card_name: '{card_payload.get('card_name')}'")

        image_key = self._generate_image_key(
            original_card_name, orientation
        )

        rating_slug = self._generate_rating_slug({
            **card_payload,
            'card_name_en': original_card_name
        })
        if rating_slug:
            card_payload = {**card_payload, 'card_id': rating_slug}
        else:
            logging.warning(
                f"⚠️ Failed to generate rating slug for card_name_en='{original_card_name}'"
            )

        return {
            "card": card_payload,
            "orientation": orientation,
            "image_key": image_key
        }

    def _generate_image_key(self, card_name: str, orientation: str) -> str:
        """生成前端可直接使用的图片路径key"""
        import logging
        logging.info(f"🔍 _generate_image_key called with: card_name='{card_name}', orientation='{orientation}'")

        # 防御性检查:如果 card_name 为空,返回默认值
        if not card_name or card_name.strip() == "":
            logging.error(f"❌ card_name 为空,无法生成 image_key")
            return "fool"  # 返回默认的愚者牌

        special_map = {
            "Wheel of Fortune": "fortune_wheel",
            "The Hanged Man": "hanged_man",
            "The High Priestess": "high_priestess"
        }

        name_lower = card_name.lower()
        is_minor = " of " in name_lower and card_name not in special_map

        logging.info(f"🔍 name_lower='{name_lower}', is_minor={is_minor}")

        if orientation == "reversed":
            if card_name in special_map:
                base = special_map[card_name]
            elif is_minor:
                parts = name_lower.split(" of ")
                suit = parts[1].replace(" ", "_")
                rank = parts[0].replace(" ", "_")
                base = f"{rank}_{suit}"
            else:
                base = name_lower.replace("the ", "").replace(" ", "_")
            result = f"reversed/{base}_reversed"
            logging.info(f"🔍 Generated reversed image_key: {result}")
            return result

        if is_minor:
            parts = name_lower.split(" of ")
            suit = parts[1].replace(" ", "_")
            rank = parts[0].replace(" ", "_")
            result = f"{suit}/{rank}_{suit}"
            logging.info(f"🔍 Generated minor arcana image_key: {result}")
            return result
        else:
            if card_name in special_map:
                base = special_map[card_name]
            else:
                base = name_lower.replace("the ", "").replace(" ", "_")
            result = f"major/{base}"
            logging.info(f"🔍 Generated major arcana image_key: {result}")
            return result

    def _generate_rating_slug(self, card_data: Dict[str, Any]) -> str:
        """生成评分用的 tarot_offset key（如 19_sun 或 w_ace）。"""
        import logging

        name_en = (card_data.get('card_name_en') or card_data.get('card_name') or '').strip()
        if not name_en:
            return ""

        name_key = name_en.lower()
        arcana_type = (card_data.get('arcana_type') or '').lower()
        suit = (card_data.get('suit') or '').lower()

        major_map = {
            'the fool': '0_fool',
            'the magician': '1_magician',
            'the high priestess': '2_priestess',
            'the empress': '3_empress',
            'the emperor': '4_emperor',
            'the hierophant': '5_hierophant',
            'the lovers': '6_lovers',
            'the chariot': '7_chariot',
            'strength': '8_strength',
            'the hermit': '9_hermit',
            'wheel of fortune': '10_wheel',
            'justice': '11_justice',
            'the hanged man': '12_hanged_man',
            'death': '13_death',
            'temperance': '14_temperance',
            'the devil': '15_devil',
            'the tower': '16_tower',
            'the star': '17_star',
            'the moon': '18_moon',
            'the sun': '19_sun',
            'judgement': '20_judgement',
            'the world': '21_world'
        }

        # Major arcana
        if 'major' in arcana_type or name_key in major_map:
            slug = major_map.get(name_key)
            if slug:
                return slug

        # Minor arcana
        minor_suit_map = {
            'wands': 'w',
            'rods': 'w',
            'staves': 'w',
            'cups': 'c',
            'chalices': 'c',
            'swords': 's',
            'pentacles': 'p',
            'coins': 'p'
        }
        minor_rank_map = {
            'ace': 'ace',
            'page': 'page',
            'knight': 'knight',
            'queen': 'queen',
            'king': 'king',
            'two': '2',
            'three': '3',
            'four': '4',
            'five': '5',
            'six': '6',
            'seven': '7',
            'eight': '8',
            'nine': '9',
            'ten': '10',
            '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10'
        }

        # Case: name like "Ace of Wands"
        if ' of ' in name_key:
            rank_raw, suit_raw = name_key.split(' of ', 1)
            rank_slug = minor_rank_map.get(rank_raw)
            suit_slug = minor_suit_map.get(suit_raw)
            if rank_slug and suit_slug:
                return f"{suit_slug}_{rank_slug}"

        # Fallback: use suit field + name as rank
        suit_slug = minor_suit_map.get(suit)
        if suit_slug:
            rank_slug = minor_rank_map.get(name_key)
            if rank_slug:
                return f"{suit_slug}_{rank_slug}"

        logging.warning(
            f"⚠️ Could not map tarot card to rating slug: name_en='{name_en}', suit='{suit}', arcana_type='{arcana_type}'"
        )
        return ""


tarot_service = TarotService()
