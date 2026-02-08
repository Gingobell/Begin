from typing import Dict


class SpecialPatternService:
    """八字特殊格局/干支组合计算服务 V3.3"""

    def __init__(self):
        self.GOD_TYPES = {
            '正印': 'Resource', '偏印': 'Resource',
            '比肩': 'Peer', '劫财': 'Peer',
            '食神': 'Output', '伤官': 'Output',
            '正财': 'Wealth', '偏财': 'Wealth',
            '正官': 'Power', '七杀': 'Power'
        }

    def get_god_type(self, god: str) -> str:
        return self.GOD_TYPES.get(god, 'Unknown')

    def calculate_pattern_score(self, stem_god: str, branch_god: str) -> Dict[str, float]:
        s_type = self.get_god_type(stem_god)
        b_type = self.get_god_type(branch_god)
        scores = {"career": 0, "wealth": 0, "love": 0, "study": 0, "social": 0}

        if (stem_god == '伤官' and branch_god == '正官') or (stem_god == '正官' and branch_god == '伤官'):
            return {"career": -20, "wealth": -10, "love": -15, "study": -10, "social": -15}
        if (s_type == 'Resource' and b_type == 'Output') or (s_type == 'Output' and b_type == 'Resource'):
            return {"career": -10, "wealth": -10, "love": -5, "study": 5, "social": -10}
        if (s_type == 'Wealth' and branch_god == '七杀') or (stem_god == '七杀' and b_type == 'Wealth'):
            return {"career": -5, "wealth": -15, "love": -10, "study": -10, "social": -5}
        if (s_type == 'Peer' and b_type == 'Wealth') or (s_type == 'Wealth' and b_type == 'Peer'):
            return {"career": -5, "wealth": -15, "love": -10, "study": 0, "social": 5}
        if (s_type == 'Output' and branch_god == '七杀') or (stem_god == '七杀' and b_type == 'Output'):
            return {"career": 20, "wealth": 10, "love": -5, "study": 10, "social": 15}
        if (s_type == 'Power' and b_type == 'Resource') or (s_type == 'Resource' and b_type == 'Power'):
            return {"career": 20, "wealth": 5, "love": 10, "study": 20, "social": 10}
        if (s_type == 'Output' and b_type == 'Wealth') or (s_type == 'Wealth' and b_type == 'Output'):
            return {"career": 10, "wealth": 20, "love": 10, "study": -5, "social": 10}
        if (s_type == 'Wealth' and b_type == 'Power') or (s_type == 'Power' and b_type == 'Wealth'):
            return {"career": 15, "wealth": 10, "love": 10, "study": 0, "social": 10}
        if (s_type == 'Resource' and b_type == 'Peer') or (s_type == 'Peer' and b_type == 'Resource'):
            return {"career": 5, "wealth": 5, "love": 5, "study": 15, "social": 15}
        if (s_type == 'Power' and b_type == 'Peer') or (s_type == 'Peer' and b_type == 'Power'):
            return {"career": 15, "wealth": 10, "love": 5, "study": 5, "social": -5}
        if s_type == b_type:
            if s_type == 'Output': return {"career": 10, "wealth": 15, "love": 10, "study": 5, "social": 15}
            if s_type == 'Wealth': return {"career": 5, "wealth": 20, "love": 15, "study": -10, "social": 5}
            if s_type == 'Resource': return {"career": -5, "wealth": -5, "love": -5, "study": 20, "social": -5}
            if s_type == 'Peer': return {"career": 0, "wealth": -15, "love": -10, "study": 0, "social": 20}
            if stem_god == '七杀': return {"career": 10, "wealth": -5, "love": -5, "study": -5, "social": -5}

        return scores


special_pattern_service = SpecialPatternService()
