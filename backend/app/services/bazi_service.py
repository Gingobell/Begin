from cnlunar import Lunar
import sxtwl  # 以节气（立春）为界的干支计算
from datetime import date, datetime
from typing import Dict, Optional, Set, List
import logging
from .bazi_translations import (
    translate_heavenly_stem,
    translate_ten_god,
    translate_ten_god_analysis
)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BaZiService:
    """
    八字核心服务 V1.3 (Dynamic Season Interaction)
    
    更新日志:
    - 权重重构: 月令(60) + 日支(15) + 年支(10) + 月干(10) + 年干(5) = 100
    - 月令动态: 引入冲合折损逻辑 (合x0.85, 冲x0.7)，土支逢冲不减分
    - 藏干通根: 地支和天干判定引入藏干 (Hidden Stems) 支持
    - 阈值调整: Strong >= 50
    """

    # =========================================================================
    # 1. 基础配置数据 (Configuration)
    # =========================================================================
    
    # 天干配置：五行与阴阳
    HEAVENLY_STEMS = { 
        '甲': {'element': '木', 'yin_yang': '阳'}, '乙': {'element': '木', 'yin_yang': '阴'},
        '丙': {'element': '火', 'yin_yang': '阳'}, '丁': {'element': '火', 'yin_yang': '阴'},
        '戊': {'element': '土', 'yin_yang': '阳'}, '己': {'element': '土', 'yin_yang': '阴'},
        '庚': {'element': '金', 'yin_yang': '阳'}, '辛': {'element': '金', 'yin_yang': '阴'},
        '壬': {'element': '水', 'yin_yang': '阳'}, '癸': {'element': '水', 'yin_yang': '阴'}
    }
    
    # 地支配置：五行、藏干、库气
    # 【V1.3 更新】补全 hidden_stems (藏干列表) 以支持余气通根
    EARTHLY_BRANCHES = {
        '子': {'element': '水', 'main_hidden_stem': '癸', 'hidden_stems': ['癸'], 'is_storage': False}, 
        '丑': {'element': '土', 'main_hidden_stem': '己', 'hidden_stems': ['己', '癸', '辛'], 'is_storage': True},  # 金库
        '寅': {'element': '木', 'main_hidden_stem': '甲', 'hidden_stems': ['甲', '丙', '戊'], 'is_storage': False},
        '卯': {'element': '木', 'main_hidden_stem': '乙', 'hidden_stems': ['乙'], 'is_storage': False}, 
        '辰': {'element': '土', 'main_hidden_stem': '戊', 'hidden_stems': ['戊', '乙', '癸'], 'is_storage': True},  # 水库
        '巳': {'element': '火', 'main_hidden_stem': '丙', 'hidden_stems': ['丙', '庚', '戊'], 'is_storage': False}, # 庚金长生
        '午': {'element': '火', 'main_hidden_stem': '丁', 'hidden_stems': ['丁', '己'], 'is_storage': False}, 
        '未': {'element': '土', 'main_hidden_stem': '己', 'hidden_stems': ['己', '丁', '乙'], 'is_storage': True},  # 木库
        '申': {'element': '金', 'main_hidden_stem': '庚', 'hidden_stems': ['庚', '壬', '戊'], 'is_storage': False},
        '酉': {'element': '金', 'main_hidden_stem': '辛', 'hidden_stems': ['辛'], 'is_storage': False}, 
        '戌': {'element': '土', 'main_hidden_stem': '戊', 'hidden_stems': ['戊', '辛', '丁'], 'is_storage': True},  # 火库
        '亥': {'element': '水', 'main_hidden_stem': '壬', 'hidden_stems': ['壬', '甲'], 'is_storage': False}
    }

    # 五行生克关系
    ELEMENT_RELATIONS = {
        '木': {'generates': '火', 'overcomes': '土', 'generated_by': '水'}, 
        '火': {'generates': '土', 'overcomes': '金', 'generated_by': '木'},
        '土': {'generates': '金', 'overcomes': '水', 'generated_by': '火'}, 
        '金': {'generates': '水', 'overcomes': '木', 'generated_by': '土'},
        '水': {'generates': '木', 'overcomes': '火', 'generated_by': '金'}
    }

    # 地支三合/三会局配置
    COMBINATIONS = {
        '木': [{'寅', '卯', '辰'}, {'亥', '卯', '未'}],
        '火': [{'巳', '午', '未'}, {'寅', '午', '戌'}],
        '金': [{'申', '酉', '戌'}, {'巳', '酉', '丑'}],
        '水': [{'亥', '子', '丑'}, {'申', '子', '辰'}],
        '土': [{'辰', '戌', '丑', '未'}]
    }

    # 十二长生查找表
    TWELVE_PHASES_MAP = {
        '甲': {'亥': '长生', '子': '沐浴', '丑': '冠带', '寅': '临官', '卯': '帝旺', '辰': '衰', '巳': '病', '午': '死', '未': '墓', '申': '绝', '酉': '胎', '戌': '养'},
        '乙': {'午': '长生', '巳': '沐浴', '辰': '冠带', '卯': '临官', '寅': '帝旺', '丑': '衰', '子': '病', '亥': '死', '戌': '墓', '酉': '绝', '申': '胎', '未': '养'},
        '丙': {'寅': '长生', '卯': '沐浴', '辰': '冠带', '巳': '临官', '午': '帝旺', '未': '衰', '申': '病', '酉': '死', '戌': '墓', '亥': '绝', '子': '胎', '丑': '养'},
        '戊': {'寅': '长生', '卯': '沐浴', '辰': '冠带', '巳': '临官', '午': '帝旺', '未': '衰', '申': '病', '酉': '死', '戌': '墓', '亥': '绝', '子': '胎', '丑': '养'},
        '丁': {'酉': '长生', '申': '沐浴', '未': '冠带', '午': '临官', '巳': '帝旺', '辰': '衰', '卯': '病', '寅': '死', '丑': '墓', '子': '绝', '亥': '胎', '戌': '养'},
        '己': {'酉': '长生', '申': '沐浴', '未': '冠带', '午': '临官', '巳': '帝旺', '辰': '衰', '卯': '病', '寅': '死', '丑': '墓', '子': '绝', '亥': '胎', '戌': '养'},
        '庚': {'巳': '长生', '午': '沐浴', '未': '冠带', '申': '临官', '酉': '帝旺', '戌': '衰', '亥': '病', '子': '死', '丑': '墓', '寅': '绝', '卯': '胎', '辰': '养'},
        '辛': {'子': '长生', '亥': '沐浴', '戌': '冠带', '酉': '临官', '申': '帝旺', '未': '衰', '午': '病', '巳': '死', '辰': '墓', '卯': '绝', '寅': '胎', '丑': '养'},
        '壬': {'申': '长生', '酉': '沐浴', '戌': '冠带', '亥': '临官', '子': '帝旺', '丑': '衰', '寅': '病', '卯': '死', '辰': '墓', '巳': '绝', '午': '胎', '未': '养'},
        '癸': {'卯': '长生', '寅': '沐浴', '丑': '冠带', '子': '临官', '亥': '帝旺', '戌': '衰', '酉': '病', '申': '死', '未': '墓', '午': '绝', '巳': '胎', '辰': '养'}
    }

    # 冲合关系配置
    SIX_CLASHES = {'子': '午', '午': '子', '丑': '未', '未': '丑', '寅': '申', '申': '寅', '卯': '酉', '酉': '卯', '辰': '戌', '戌': '辰', '巳': '亥', '亥': '巳'}
    SIX_COMBINES = {'子': '丑', '丑': '子', '寅': '亥', '亥': '寅', '卯': '戌', '戌': '卯', '辰': '酉', '酉': '辰', '巳': '申', '申': '巳', '午': '未', '未': '午'}
    TRIANGLE_COMBINES = {'子': ['申', '辰'], '申': ['子', '辰'], '辰': ['子', '申'], '亥': ['卯', '未'], '卯': ['亥', '未'], '未': ['亥', '卯'], '寅': ['午', '戌'], '午': ['寅', '戌'], '戌': ['寅', '午'], '巳': ['酉', '丑'], '酉': ['巳', '丑'], '丑': ['巳', '酉']}
    SIX_HARMS = {'子': '未', '未': '子', '丑': '午', '午': '丑', '寅': '巳', '巳': '寅', '卯': '辰', '辰': '卯', '申': '亥', '亥': '申', '酉': '戌', '戌': '酉'}
    PUNISHMENTS = {'子': ['卯'], '卯': ['子'], '寅': ['巳', '申'], '巳': ['寅', '申'], '申': ['寅', '巳'], '丑': ['戌', '未'], '戌': ['丑', '未'], '未': ['丑', '戌']}

    # =========================================================================
    # 2. 核心公共方法 (Public Methods)
    # =========================================================================

    def calculate_bazi(self, birth_date: date) -> Dict:
        """
        计算八字基础信息及用户体质（电池容量）
        """
        lunar_date = Lunar(datetime.combine(birth_date, datetime.min.time()))
        
        year_pillar_str = lunar_date.year8Char
        month_pillar_str = lunar_date.month8Char
        day_pillar_str = lunar_date.day8Char
        hour_pillar_str = lunar_date.twohour8Char 
        
        day_master = day_pillar_str[0] 

        # 构建结构化数据
        bazi_structure = {
            'year': {'stem': year_pillar_str[0], 'branch': year_pillar_str[1]},
            'month': {'stem': month_pillar_str[0], 'branch': month_pillar_str[1]},
            'day': {'stem': day_pillar_str[0], 'branch': day_pillar_str[1]}
        }

        # 计算体质 (V1.3)
        body_strength = self.calculate_body_strength(day_master, bazi_structure)
        logging.info(f"🔋 用户体质判定完成: {day_master}日主 -> {body_strength}")

        return { 
            "day_master": day_master, 
            "year_pillar": year_pillar_str, 
            "month_pillar": month_pillar_str, 
            "day_pillar": day_pillar_str, 
            "hour_pillar": hour_pillar_str,
            "body_strength": body_strength
        }

    def calculate_body_strength(self, day_master: str, pillars: Dict) -> str:
        """
        Phase 0: 用户体质检测 (V1.3 动态月令权重版)
        逻辑权重: 
        - 月令 (60): 包含动态环境检测 (冲x0.7, 合x0.85, 土例外)
        - 日支 (15): 贴身
        - 年支 (10): 根基
        - 月干 (10): 近身
        - 年干 (05): 远端
        """
        dm_element = self.HEAVENLY_STEMS[day_master]['element']
        branches = {pillars['year']['branch'], pillars['month']['branch'], pillars['day']['branch']}
        
        # 1. 局气判定 (The Override) - 最高优先级
        override_result = self._check_bureau_override(dm_element, branches)
        if override_result:
            return override_result

        # 2. 三柱加权计算 (Weighted Scoring)
        score = 0.0
        
        # A. 月令 (权重 60) - 升级为动态算法
        # 需传入 pillars 用于检测月令和年/日的关系
        score += self._score_season_dynamic(dm_element, pillars)
        
        # B. 得地-日支 (权重 15)
        score += self._score_root(dm_element, pillars['day']['branch'], weight=15)
        
        # C. 得地-年支 (权重 10)
        score += self._score_root(dm_element, pillars['year']['branch'], weight=10)
        
        # D. 得势-月干 (权重 10)
        score += self._score_stem_support(dm_element, pillars['month']['stem'], pillars['month']['branch'], 10)
        
        # E. 得势-年干 (权重 05) - 降权
        score += self._score_stem_support(dm_element, pillars['year']['stem'], pillars['year']['branch'], 5)
        
        logging.info(f"📊 体质评分总分: {score}")

        # 3. 容量定档 (阈值调整)
        if score >= 50:
            return 'Strong'
        elif score >= 30:
            return 'Balanced'
        else:
            return 'Weak'

    def get_12_phase(self, day_master: str, branch: str) -> str:
        """获取十二长生状态"""
        stem_map = self.TWELVE_PHASES_MAP.get(day_master)
        if not stem_map:
            logging.error(f"❌ 无法找到日主 {day_master} 的长生映射表")
            return "未知"
        return stem_map.get(branch, "未知")

    # sxtwl 天干地支索引表
    _TG_LIST = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    _DZ_LIST = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

    def analyze_daily_flow(self, birth_date: date, target_date: Optional[date] = None, language: str = "zh-CN") -> Dict:
        """分析当日流日运势"""
        bazi_data = self.calculate_bazi(birth_date)
        day_master_char = bazi_data['day_master']
        body_strength = bazi_data['body_strength']

        # 获取用户日支用于后续判断
        user_day_branch = bazi_data['day_pillar'][1]
        year_stem_char = bazi_data['year_pillar'][0]

        if target_date:
            flow_datetime = datetime.combine(target_date, datetime.min.time())
        else:
            flow_datetime = datetime.now()

        # 使用 sxtwl 以节气（立春）为界计算流年/流月/流日干支
        day = sxtwl.fromSolar(flow_datetime.year, flow_datetime.month, flow_datetime.day)
        flow_year_stem = self._TG_LIST[day.getYearGZ().tg]
        flow_year_branch = self._DZ_LIST[day.getYearGZ().dz]
        flow_month_stem = self._TG_LIST[day.getMonthGZ().tg]
        flow_month_branch = self._DZ_LIST[day.getMonthGZ().dz]
        daily_stem = self._TG_LIST[day.getDayGZ().tg]
        daily_branch = self._DZ_LIST[day.getDayGZ().dz]

        stem_relation_raw = self._get_ten_god_relation(day_master_char, daily_stem)
        branch_main_stem = self.EARTHLY_BRANCHES[daily_branch]['main_hidden_stem']
        branch_relation_raw = self._get_ten_god_relation(day_master_char, branch_main_stem)

        energy_phase = self.get_12_phase(day_master_char, daily_branch)
        branch_relation_type = self._get_branch_relationship(user_day_branch, daily_branch)

        nobleman_score = self._calculate_nobleman_score(
            day_master_char, year_stem_char, daily_branch, user_day_branch
        )

        result = {
            "day_master": translate_heavenly_stem(day_master_char, language),
            "body_strength": body_strength,
            "energy_phase": energy_phase,
            "stem_influence": {
                "relation": translate_ten_god(stem_relation_raw, language),
                "raw": stem_relation_raw,
                "analysis": translate_ten_god_analysis(stem_relation_raw, language)
            },
            "branch_influence": {
                "relation": translate_ten_god(branch_relation_raw, language),
                "raw": branch_relation_raw,
                "analysis": translate_ten_god_analysis(branch_relation_raw, language),
                "relation_type": branch_relation_type
            },
            "flow_year": {"stem": flow_year_stem, "branch": flow_year_branch},
            "flow_month": {"stem": flow_month_stem, "branch": flow_month_branch},
            "flow_day": {"stem": daily_stem, "branch": daily_branch},
            # 兼容旧字段名
            "daily_pillar": {"stem": daily_stem, "branch": daily_branch},
            "nobleman_score": nobleman_score
        }

        # Log warning for any missing required fields
        required_fields = {
            "day_master": result.get("day_master"),
            "body_strength": result.get("body_strength"),
            "energy_phase": result.get("energy_phase"),
            "flow_year.stem": result.get("flow_year", {}).get("stem"),
            "flow_year.branch": result.get("flow_year", {}).get("branch"),
            "flow_month.stem": result.get("flow_month", {}).get("stem"),
            "flow_month.branch": result.get("flow_month", {}).get("branch"),
            "flow_day.stem": result.get("flow_day", {}).get("stem"),
            "flow_day.branch": result.get("flow_day", {}).get("branch"),
            "stem_influence.relation": result.get("stem_influence", {}).get("relation"),
            "branch_influence.relation": result.get("branch_influence", {}).get("relation"),
        }
        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            logging.warning(f"八字分析缺少必要字段: {', '.join(missing)} (birth_date={birth_date}, target_date={target_date})")

        return result

    # =========================================================================
    # 3. 辅助计算逻辑 (Internal Helpers)
    # =========================================================================

    def _get_branch_relationship(self, branch1: str, branch2: str) -> str:
        """
        判断两个地支的关系 (通用方法)
        返回: 'clash', 'combine', '3-combine', 'harm', 'punish', 'none'
        """
        if self.SIX_CLASHES.get(branch1) == branch2: return 'clash'
        if self.SIX_COMBINES.get(branch1) == branch2: return 'combine'
        if branch2 in self.TRIANGLE_COMBINES.get(branch1, []): return '3-combine'
        if branch1 == branch2 and branch1 in ['辰', '午', '酉', '亥']: return 'punish'
        if branch2 in self.PUNISHMENTS.get(branch1, []): return 'punish'
        if self.SIX_HARMS.get(branch1) == branch2: return 'harm'
        return 'none'

    def _check_bureau_override(self, dm_element: str, branches: Set[str]) -> Optional[str]:
        """检查地支成局"""
        for element, combos in self.COMBINATIONS.items():
            for combo in combos:
                if combo.issubset(branches): 
                    relation = self._get_element_relation(dm_element, element)
                    if relation == 'same' or relation == 'generated_by':
                        logging.info(f"🔋 局气判定: 地支成 {element} 局 (帮身) -> 锁定 Strong")
                        return 'Strong'
                    if relation in ['overcomes', 'generates', 'overcome_by']:
                        logging.info(f"🪫 局气判定: 地支成 {element} 局 (克泄耗) -> 锁定 Weak")
                        return 'Weak'
        return None

    def _score_season_dynamic(self, dm_el: str, pillars: Dict) -> float:
        """
        【V1.3 核心升级】动态月令评分
        权重 60，但受环境冲合影响而折损。
        """
        month_branch = pillars['month']['branch']
        year_branch = pillars['year']['branch']
        day_branch = pillars['day']['branch']
        
        mb_info = self.EARTHLY_BRANCHES[month_branch]
        relation = self._get_element_relation(dm_el, mb_info['element'])
        
        # 1. 基础得分计算 (满分 60)
        base_score = 0.0
        if relation == 'same': base_score = 60.0         # 得令 (100% of 60)
        elif relation == 'generated_by': base_score = 45.0 # 得生 (75% of 60)
        elif mb_info['element'] == '土': base_score = 15.0 # 库气 (25% of 60)
        else: return 0.0 # 失令直接0分
        
        # 2. 动态环境检测 (月令是否被冲/合)
        multiplier = 1.0
        is_clashed = False
        is_combined = False
        
        # 检查 月 vs 年
        rel_year = self._get_branch_relationship(month_branch, year_branch)
        if rel_year == 'clash': is_clashed = True
        elif rel_year in ['combine', '3-combine']: is_combined = True
        
        # 检查 月 vs 日
        rel_day = self._get_branch_relationship(month_branch, day_branch)
        if rel_day == 'clash': is_clashed = True
        elif rel_day in ['combine', '3-combine']: is_combined = True
        
        # 3. 应用折损逻辑
        if is_clashed:
            # 特殊规则：土支逢冲不减分 (辰戌丑未)
            if mb_info['element'] == '土':
                logging.info(f"🧱 月令{month_branch}为土且被冲，土越冲越旺，能量不折损 (1.0)")
                multiplier = 1.0
            else:
                logging.info(f"💥 月令{month_branch}被冲，能量散失 (x0.7)")
                multiplier = 0.7
        elif is_combined:
            # 被合绊住 (贪合忘生/助)
            logging.info(f"🔗 月令{month_branch}被合，能量减弱 (x0.85)")
            multiplier = 0.85
            
        final_score = base_score * multiplier
        logging.debug(f"🌙 月令最终得分: {base_score} * {multiplier} = {final_score}")
        
        return final_score

    def _score_root(self, dm_el: str, branch: str, weight: float) -> float:
        """
        得地得分：支持藏干通根 (V1.3)
        """
        branch_info = self.EARTHLY_BRANCHES[branch]
        main_el = branch_info['element']
        
        # 1. 本气强根 (100%)
        if self._get_element_relation(dm_el, main_el) == 'same': 
            return float(weight) 
        
        # 2. 印/库 (60%)
        if self._get_element_relation(dm_el, main_el) == 'generated_by' or branch_info['is_storage']:
            return weight * 0.6 
            
        # 3. 余气/中气通根 (30%) - 检查藏干
        if 'hidden_stems' in branch_info:
            for stem in branch_info['hidden_stems']:
                stem_el = self.HEAVENLY_STEMS[stem]['element']
                if self._get_element_relation(dm_el, stem_el) == 'same':
                    # 发现余气根
                    return weight * 0.3
        
        return 0.0

    def _score_stem_support(self, dm_el: str, stem: str, sitting_branch: str, base_weight: float) -> float:
        """
        得势得分：支持坐支藏干救赎 (V1.3)
        """
        stem_el = self.HEAVENLY_STEMS[stem]['element']
        relation = self._get_element_relation(dm_el, stem_el)
        
        # 只有印比帮身才算分
        if relation not in ['same', 'generated_by']: return 0.0
        
        # 检查坐支关系
        sit_b_info = self.EARTHLY_BRANCHES[sitting_branch]
        sit_b_el = sit_b_info['element']
        stem_sit_rel = self._get_element_relation(stem_el, sit_b_el)
        
        coeff = 0.6
        
        # 1. 有力 (本气生助)
        if stem_sit_rel in ['same', 'generated_by']: 
            coeff = 1.0 
        
        # 2. 坐支救赎 (藏干通气) - NEW
        # 如果本气不帮，但藏干里有帮的，系数提升
        elif 'hidden_stems' in sit_b_info:
            for hidden in sit_b_info['hidden_stems']:
                if self.HEAVENLY_STEMS[hidden]['element'] == stem_el:
                    coeff = 0.7  # 从截脚 0.3 提升至 0.7
                    break
        
        # 3. 截脚 (如无救赎)
        elif stem_sit_rel == 'overcome_by': 
            if coeff == 0.6: coeff = 0.3
        
        return base_weight * coeff

    def _get_element_relation(self, me: str, other: str) -> str:
        """五行关系判断"""
        if me == other: return 'same'
        if self.ELEMENT_RELATIONS[me]['generates'] == other: return 'generates'
        if self.ELEMENT_RELATIONS[me]['overcomes'] == other: return 'overcomes'
        if self.ELEMENT_RELATIONS[me]['generated_by'] == other: return 'generated_by'
        return 'overcome_by'

    def _calculate_nobleman_score(self, day_master: str, year_stem: str, daily_branch: str, user_day_branch: str) -> int:
        """计算天乙贵人分"""
        nobleman_map = {
            '甲': ['丑', '未'], '戊': ['丑', '未'], '庚': ['丑', '未'],
            '乙': ['子', '申'], '己': ['子', '申'],
            '丙': ['亥', '酉'], '丁': ['亥', '酉'],
            '壬': ['巳', '卯'], '癸': ['巳', '卯'],
            '辛': ['午', '寅']
        }
        score = 0
        if daily_branch in nobleman_map.get(day_master, []):
            score += 15
        if daily_branch in nobleman_map.get(year_stem, []):
            score += 10
        if score > 20:
            score = 20

        if self._get_branch_relationship(user_day_branch, daily_branch) == 'clash':
            score = int(score * 0.5)

        return score

    def _get_ten_god_relation(self, day_master_char: str, other_stem_char: str) -> str:
        """十神关系判断"""
        day_master = self.HEAVENLY_STEMS[day_master_char]
        other_stem = self.HEAVENLY_STEMS[other_stem_char]
        
        me_el = day_master['element']
        other_el = other_stem['element']
        same_yin_yang = day_master['yin_yang'] == other_stem['yin_yang']

        if me_el == other_el: return '比肩' if same_yin_yang else '劫财'
        if self.ELEMENT_RELATIONS[me_el]['generates'] == other_el: return '食神' if same_yin_yang else '伤官'
        if self.ELEMENT_RELATIONS[other_el]['generates'] == me_el: return '偏印' if same_yin_yang else '正印'
        if self.ELEMENT_RELATIONS[me_el]['overcomes'] == other_el: return '偏财' if same_yin_yang else '正财'
        if self.ELEMENT_RELATIONS[other_el]['overcomes'] == me_el: return '七杀' if same_yin_yang else '正官'
        return "未知关系"

# 创建单例
bazi_service = BaZiService()
