import logging
from typing import Dict
from dataclasses import dataclass
from .special_pattern_service import special_pattern_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@dataclass
class FortuneResult:
    overall_score: int
    body_strength: str
    low_power_mode: bool
    domain_scores: Dict[str, int]
    bazi_modifiers: Dict[str, float]
    tarot_modifiers: Dict[str, float]
    domain_tarot_contribution: Dict[str, float]
    is_major_arcana: bool


class FortuneScoringEngine:
    """🔋 电池运势核心引擎 V3.3"""

    def __init__(self):
        self.BASE_SCORE = 65.0
        self.MIN_SCORE = 30.0
        self.MAX_SCORE = 100.0
        self.BAZI_SOFT_CAP = 90.0
        self.TAROT_MULTIPLIER_MINOR = 5.0
        self.TAROT_MULTIPLIER_MAJOR = 6.0
        self.FIERCE_GODS = ['七杀', '伤官', '劫财', '偏印']
        self.AUSPICIOUS_GODS = ['正官', '食神', '正印', '正财', '偏财', '比肩']

        self.TAROT_OFFSETS = {
            "0_fool": {"overall": 0.5, "career": 0.2, "study": 0.5, "love": 0.5, "wealth": -0.5, "social": 1.5},
            "1_magician": {"overall": 1.5, "career": 1.5, "study": 1.5, "love": 0.8, "wealth": 1.2, "social": 1.5},
            "2_priestess": {"overall": 0.5, "career": 0, "study": 1.8, "love": -0.5, "wealth": 0, "social": -0.5},
            "3_empress": {"overall": 1.5, "career": 0.5, "study": 0.5, "love": 1.8, "wealth": 1.5, "social": 1.5},
            "4_emperor": {"overall": 1.2, "career": 2.0, "study": 0.5, "love": 0.5, "wealth": 1.5, "social": 0.8},
            "5_hierophant": {"overall": 0.5, "career": 1.0, "study": 1.5, "love": 0.5, "wealth": 0, "social": 1.2},
            "6_lovers": {"overall": 1.2, "career": 0.5, "study": 0, "love": 2.0, "wealth": 0, "social": 1.5},
            "7_chariot": {"overall": 1.2, "career": 2.0, "study": 1.0, "love": 0.5, "wealth": 0.8, "social": 0},
            "8_strength": {"overall": 1.0, "career": 1.5, "study": 0.8, "love": 1.2, "wealth": 0.5, "social": 0.8},
            "9_hermit": {"overall": 0, "career": -0.5, "study": 1.8, "love": -1.5, "wealth": 0, "social": -2.0},
            "10_wheel": {"overall": 1.8, "career": 1.2, "study": 0.5, "love": 1.0, "wealth": 1.5, "social": 0.8},
            "11_justice": {"overall": 0.5, "career": 1.2, "study": 1.2, "love": 0.2, "wealth": 0, "social": 0},
            "12_hanged_man": {"overall": -0.5, "career": -1.0, "study": 1.0, "love": -0.5, "wealth": -0.8, "social": -0.5},
            "13_death": {"overall": -1.5, "career": -1.5, "study": -0.5, "love": -1.5, "wealth": -1.0, "social": -1.0},
            "14_temperance": {"overall": 1.2, "career": 0.8, "study": 1.0, "love": 1.0, "wealth": 0.5, "social": 1.5},
            "15_devil": {"overall": -1.2, "career": 0.5, "study": -1.0, "love": -2.0, "wealth": 1.5, "social": -1.5},
            "16_tower": {"overall": -2.0, "career": -2.0, "study": -1.8, "love": -2.0, "wealth": -2.0, "social": -2.0},
            "17_star": {"overall": 1.5, "career": 0.8, "study": 1.2, "love": 1.2, "wealth": 0.5, "social": 1.0},
            "18_moon": {"overall": -1.5, "career": -1.0, "study": -1.2, "love": -1.5, "wealth": -0.8, "social": -1.2},
            "19_sun": {"overall": 2.0, "career": 1.8, "study": 1.2, "love": 1.5, "wealth": 1.5, "social": 1.8},
            "20_judgement": {"overall": 1.5, "career": 1.5, "study": 1.0, "love": 0.8, "wealth": 0.5, "social": 0.5},
            "21_world": {"overall": 2.0, "career": 2.0, "study": 1.5, "love": 1.8, "wealth": 1.8, "social": 1.5},
            "w_ace": {"career": 2.0, "study": 1.0, "love": 0.5, "wealth": 1.0, "social": 0.8},
            "w_2": {"career": 1.0, "study": 0.8, "love": 0.2, "wealth": 0.5, "social": 0.5},
            "w_3": {"career": 1.5, "study": 1.0, "love": 0.5, "wealth": 1.0, "social": 0.5},
            "w_4": {"overall": 1.5, "career": 1.0, "study": 0.2, "love": 1.5, "wealth": 1.0, "social": 2.0},
            "w_5": {"overall": -0.5, "career": -1.2, "study": -0.5, "love": -0.8, "wealth": -0.5, "social": -2.0},
            "w_6": {"career": 2.0, "study": 1.2, "love": 0.5, "wealth": 1.0, "social": 1.8},
            "w_7": {"career": 1.0, "study": 0.8, "love": 0.2, "wealth": 0.5, "social": -0.5},
            "w_8": {"career": 1.8, "study": 1.0, "love": 0.8, "wealth": 0.8, "social": 0.5},
            "w_9": {"career": 0.5, "study": 0.5, "love": 0, "wealth": 0, "social": -0.8},
            "w_10": {"overall": -1.0, "career": -2.0, "study": -1.2, "love": -0.5, "wealth": -0.8, "social": -1.5},
            "w_page": {"career": 1.2, "study": 1.2, "love": 0.5, "wealth": 0.5, "social": 0.8},
            "w_knight": {"career": 1.8, "study": 0.5, "love": 0.8, "wealth": 0.8, "social": 0.5},
            "w_queen": {"career": 1.5, "study": 0.5, "love": 1.0, "wealth": 1.0, "social": 1.5},
            "w_king": {"career": 2.0, "study": 0.5, "love": 0.8, "wealth": 1.5, "social": 1.2},
            "c_ace": {"career": 0.5, "study": 0.5, "love": 2.0, "wealth": 0.5, "social": 1.5},
            "c_2": {"career": 0.5, "study": 0, "love": 2.0, "wealth": 0.5, "social": 1.8},
            "c_3": {"career": 0.5, "study": 0, "love": 1.2, "wealth": 0.5, "social": 2.0},
            "c_4": {"overall": -0.5, "career": -0.5, "study": -0.5, "love": -0.8, "wealth": 0, "social": -1.2},
            "c_5": {"overall": -1.0, "career": -0.8, "study": -0.8, "love": -1.8, "wealth": -0.5, "social": -1.5},
            "c_6": {"career": 0, "study": 0.5, "love": 1.5, "wealth": 0.5, "social": 1.8},
            "c_7": {"career": -0.5, "study": -1.2, "love": -0.5, "wealth": -0.5, "social": 0},
            "c_8": {"career": -1.0, "study": 0, "love": -1.5, "wealth": -0.5, "social": -1.2},
            "c_9": {"overall": 1.5, "career": 0.5, "study": 0, "love": 1.2, "wealth": 1.5, "social": 1.5},
            "c_10": {"overall": 1.8, "career": 0.5, "study": 0, "love": 2.0, "wealth": 1.2, "social": 1.8},
            "c_page": {"career": 0.5, "study": 1.0, "love": 1.5, "wealth": 0.5, "social": 1.0},
            "c_knight": {"career": 0.5, "study": 0.5, "love": 1.8, "wealth": 0.5, "social": 1.0},
            "c_queen": {"career": 0.5, "study": 0.5, "love": 1.8, "wealth": 0.5, "social": 1.5},
            "c_king": {"career": 1.0, "study": 0.5, "love": 1.5, "wealth": 0.5, "social": 1.5},
            "s_ace": {"career": 1.2, "study": 2.0, "love": 0, "wealth": 0.5, "social": 0.2},
            "s_2": {"career": -0.5, "study": 1.2, "love": 0, "wealth": 0, "social": -0.5},
            "s_3": {"overall": -1.5, "career": -0.8, "study": -0.5, "love": -2.0, "wealth": -0.5, "social": -1.5},
            "s_4": {"overall": -0.5, "career": -1.2, "study": 0.5, "love": -0.5, "wealth": 0, "social": -2.0},
            "s_5": {"overall": -1.5, "career": -1.5, "study": -0.5, "love": -1.5, "wealth": -1.0, "social": -2.0},
            "s_6": {"career": 0.5, "study": 1.0, "love": 0.5, "wealth": 0.5, "social": 0.5},
            "s_7": {"career": -0.8, "study": 0.5, "love": -1.0, "wealth": -0.5, "social": -1.2},
            "s_8": {"overall": -1.0, "career": -1.5, "study": -1.2, "love": -0.8, "wealth": -0.8, "social": -1.0},
            "s_9": {"overall": -1.5, "career": -1.2, "study": -1.0, "love": -1.2, "wealth": -0.5, "social": -1.5},
            "s_10": {"overall": -2.0, "career": -2.0, "study": -1.5, "love": -1.8, "wealth": -1.5, "social": -1.5},
            "s_page": {"career": 0.5, "study": 1.8, "love": 0, "wealth": 0.2, "social": 0.5},
            "s_knight": {"career": 1.5, "study": 1.5, "love": -0.5, "wealth": 0.5, "social": -0.8},
            "s_queen": {"career": 1.2, "study": 1.5, "love": 0.5, "wealth": 0.8, "social": 0.5},
            "s_king": {"career": 1.8, "study": 1.8, "love": 0.5, "wealth": 1.0, "social": 1.0},
            "p_ace": {"career": 1.5, "study": 0.5, "love": 0.5, "wealth": 2.0, "social": 0.5},
            "p_2": {"career": 0.5, "study": 0, "love": 0.5, "wealth": 1.0, "social": 0.8},
            "p_3": {"career": 1.8, "study": 1.5, "love": 0.5, "wealth": 1.2, "social": 1.5},
            "p_4": {"career": 0.8, "study": 0, "love": 0, "wealth": 1.8, "social": -0.8},
            "p_5": {"overall": -1.5, "career": -1.2, "study": -0.5, "love": -1.0, "wealth": -2.0, "social": -1.8},
            "p_6": {"career": 1.0, "study": 0.5, "love": 0.8, "wealth": 1.5, "social": 1.5},
            "p_7": {"career": 0.5, "study": 0.5, "love": 0.2, "wealth": 1.0, "social": 0},
            "p_8": {"career": 1.8, "study": 1.8, "love": 0.2, "wealth": 1.5, "social": 0},
            "p_9": {"overall": 1.5, "career": 1.0, "study": 0.8, "love": 0.8, "wealth": 2.0, "social": 0.5},
            "p_10": {"overall": 1.8, "career": 1.2, "study": 0.5, "love": 1.5, "wealth": 2.0, "social": 1.5},
            "p_page": {"career": 1.0, "study": 1.5, "love": 0.5, "wealth": 1.2, "social": 0.5},
            "p_knight": {"career": 1.5, "study": 0.8, "love": 0.2, "wealth": 1.8, "social": 0},
            "p_queen": {"career": 1.2, "study": 0.5, "love": 1.0, "wealth": 2.0, "social": 1.0},
            "p_king": {"career": 1.8, "study": 0.5, "love": 0.8, "wealth": 2.0, "social": 1.2},
        }

    def _calc_overall_score(self, body_strength, energy_phase, branch_relation, nobleman_score, stem_god, branch_god):
        modifier = 0.0
        if body_strength == 'Weak':
            if energy_phase in ['冠带', '临官']: modifier += 8
            elif energy_phase in ['长生', '帝旺']: modifier += 4
            elif energy_phase in ['死', '绝', '病']: modifier -= 4
        elif body_strength == 'Strong':
            if energy_phase == '长生': modifier += 4
            elif energy_phase == '帝旺': modifier -= 8
        else:
            if energy_phase in ['冠带', '临官']: modifier += 4

        clash_penalty = 0.0
        if branch_relation in ['combine', '3-combine']: modifier += 7
        elif branch_relation == 'clash':
            clash_penalty = -7.0
            modifier += clash_penalty
        elif branch_relation in ['harm', 'punish']:
            clash_penalty = -4.0
            modifier += clash_penalty

        nobleman_mod = 8 if nobleman_score >= 15 else 4 if nobleman_score > 0 else 0
        if nobleman_mod > 0:
            modifier += nobleman_mod
            if clash_penalty < 0: modifier -= clash_penalty

        stem_favorable = self._check_is_favorable(stem_god, body_strength)
        branch_favorable = self._check_is_favorable(branch_god, body_strength)
        modifier += 5.0 if stem_favorable else -5.0
        modifier += 5.0 if branch_favorable else -5.0
        if stem_god in self.FIERCE_GODS:
            modifier -= 3.0
        return self.BASE_SCORE + modifier

    def _calc_domain_modifier(self, domain, stem_god, branch_god, gender):
        score = 0.0
        vis_score = self._get_stem_visibility_score(domain, stem_god, branch_god, gender)
        score += vis_score
        pattern_scores = special_pattern_service.calculate_pattern_score(stem_god, branch_god)
        pat_score = pattern_scores.get(domain, 0.0)
        score += pat_score
        is_double_fierce = (stem_god in self.FIERCE_GODS) and (branch_god in self.FIERCE_GODS)
        is_double_auspicious = (stem_god in self.AUSPICIOUS_GODS) and (branch_god in self.AUSPICIOUS_GODS)
        if is_double_fierce: score -= 5.0
        elif is_double_auspicious: score += 5.0
        return score

    def _get_stem_visibility_score(self, domain, stem_god, branch_god, gender):
        god_type = special_pattern_service.get_god_type(stem_god)
        is_fierce = stem_god in self.FIERCE_GODS
        HIGH_POS, MID_POS, LOW_NEG, HIGH_NEG = 10.0, 5.0, -5.0, -10.0
        score, relevant, base_score = 0.0, False, 0.0

        if domain == 'career':
            if god_type == 'Power': base_score = HIGH_POS if not is_fierce else MID_POS; relevant = True
            elif god_type == 'Wealth': base_score = MID_POS; relevant = True
            elif god_type == 'Resource': base_score = MID_POS; relevant = True
            elif god_type == 'Output':
                relevant = True
                if branch_god == '七杀': base_score = HIGH_POS
                elif branch_god == '正官': base_score = HIGH_NEG
                else: base_score = LOW_NEG
            elif god_type == 'Peer': base_score = LOW_NEG; relevant = True
        elif domain == 'wealth':
            if god_type == 'Wealth': base_score = HIGH_POS; relevant = True
            elif god_type == 'Output': base_score = MID_POS; relevant = True
            elif god_type == 'Peer': base_score = HIGH_NEG; relevant = True
            elif god_type == 'Resource': base_score = LOW_NEG; relevant = True
        elif domain == 'love':
            if gender == 'Male':
                if god_type == 'Wealth': base_score = HIGH_POS; relevant = True
                elif god_type == 'Output': base_score = MID_POS; relevant = True
                elif god_type == 'Peer': base_score = HIGH_NEG; relevant = True
                elif god_type == 'Power': base_score = MID_POS; relevant = True
            else:
                if god_type == 'Power': base_score = HIGH_POS if not is_fierce else MID_POS; relevant = True
                elif god_type == 'Wealth': base_score = MID_POS; relevant = True
                elif god_type == 'Peer': base_score = HIGH_NEG; relevant = True
                elif god_type == 'Output':
                    relevant = True
                    if branch_god == '七杀': base_score = MID_POS
                    else: base_score = HIGH_NEG
        elif domain == 'study':
            if god_type in ['Resource', 'Output']: base_score = HIGH_POS; relevant = True
            elif god_type == 'Wealth': base_score = HIGH_NEG; relevant = True
        elif domain == 'social':
            if god_type == 'Peer': base_score = HIGH_POS; relevant = True
            elif god_type == 'Output': base_score = MID_POS; relevant = True
            elif stem_god == '七杀': base_score = MID_POS; relevant = True
            elif stem_god == '伤官' and branch_god == '正官': base_score = HIGH_NEG; relevant = True

        if relevant:
            score = base_score
            if score > 0:
                stem_el = self._get_element_by_god(stem_god)
                branch_el = self._get_element_by_god(branch_god)
                if stem_el and stem_el == branch_el:
                    score *= 1.5
        return score

    def _check_is_favorable(self, god, strength):
        god_type = special_pattern_service.get_god_type(god)
        if strength == 'Strong': return god_type in ['Output', 'Wealth', 'Power']
        elif strength == 'Weak': return god_type in ['Resource', 'Peer']
        else: return god != '七杀'

    def _get_element_by_god(self, god):
        mapping = {
            '比肩': 'Same', '劫财': 'Same', '食神': 'Output', '伤官': 'Output',
            '正财': 'Wealth', '偏财': 'Wealth', '正官': 'Power', '七杀': 'Power',
            '正印': 'Resource', '偏印': 'Resource'
        }
        return mapping.get(god, '')

    def _calc_phase_3_tarot(self, card_id, is_upright, domain):
        card_data = self.TAROT_OFFSETS.get(card_id, {})
        offset = card_data.get(domain, card_data.get('overall', 0.0))
        multiplier = self.TAROT_MULTIPLIER_MAJOR if self._is_major_arcana(card_id) else self.TAROT_MULTIPLIER_MINOR
        modifier = offset * multiplier
        if not is_upright: modifier *= 0.5
        return modifier

    def _is_major_arcana(self, card_id):
        if not card_id: return False
        parts = str(card_id).split('_')
        return parts[0].isdigit() and int(parts[0]) < 22 if parts and parts[0].isdigit() else False

    def calculate(self, body_strength, energy_phase, branch_relation, nobleman_score,
                  stem_god, branch_god, tarot_card_id, tarot_is_upright, gender='Male'):
        domains = ['career', 'wealth', 'love', 'study', 'social']
        bazi_mods, tarot_mods, final_scores, domain_tarot_contribution = {}, {}, {}, {}

        overall_base = self._calc_overall_score(body_strength, energy_phase, branch_relation, nobleman_score, stem_god, branch_god)
        bazi_overall_capped = min(self.BAZI_SOFT_CAP, overall_base)
        tarot_overall = self._calc_phase_3_tarot(tarot_card_id, tarot_is_upright, 'overall')
        tarot_mods['overall'] = tarot_overall
        final_overall = max(self.MIN_SCORE, min(self.MAX_SCORE, bazi_overall_capped + tarot_overall))
        bazi_mods['overall'] = overall_base - self.BASE_SCORE
        low_power_mode = final_overall < 45.0

        for domain in domains:
            domain_base = overall_base
            domain_delta = self._calc_domain_modifier(domain, stem_god, branch_god, gender)
            bazi_mods[domain] = domain_delta
            raw_bazi_domain = domain_base + domain_delta
            bazi_domain_capped = min(self.BAZI_SOFT_CAP, raw_bazi_domain)
            tarot_domain = self._calc_phase_3_tarot(tarot_card_id, tarot_is_upright, domain)
            tarot_mods[domain] = tarot_domain
            domain_tarot_contribution[domain] = tarot_domain
            score = bazi_domain_capped + tarot_domain
            final_scores[domain] = int(max(self.MIN_SCORE, min(self.MAX_SCORE, score)))

        return FortuneResult(
            overall_score=int(final_overall), body_strength=body_strength,
            low_power_mode=low_power_mode, domain_scores=final_scores,
            bazi_modifiers=bazi_mods, tarot_modifiers=tarot_mods,
            domain_tarot_contribution=domain_tarot_contribution,
            is_major_arcana=self._is_major_arcana(tarot_card_id),
        )
