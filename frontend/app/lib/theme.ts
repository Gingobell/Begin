// ── Theme config (shared across app) ────────────────────────────
export const T = {
  cream: "#FDFBF8",
  coral: { p: "#FF6B4A", s: "#FF8A6A", soft: "#FFB89A", airy: "#FFF5F0", cream: "#FFFBFA" },
  blue: { p: "#5C8BFF", s: "#7AA3FF", soft: "#A8C4FF", airy: "#E6F0FF" },
  purple: { p: "#8F6BF7", s: "#9B7DF9", soft: "#D4C5FF", airy: "#F0ECFF" },
  honey: { p: "#FFD75A", s: "#FFE073", soft: "#FFEEB0", airy: "#FFFBF0" },
  career: { p: "#7DD3FC", s: "#9BDFFD", soft: "#C0EBFE", airy: "#EAF8FF", cream: "#F5FAFF" },
  love: { p: "#FFB8D0", s: "#FFCBDD", soft: "#FFE0EB", airy: "#FFF6F9", cream: "#FFF8FA" },
  wealth: { p: "#F2D94D", s: "#F7E36B", soft: "#FAEEB0", airy: "#FDF9E6", cream: "#FFFCF0" },
  study: { p: "#7DDFBD", s: "#9BE8CF", soft: "#C0F0E0", airy: "#E8FBF5", cream: "#F5FCF8" },
  social: { p: "#B8A4FF", s: "#CBBAFE", soft: "#E0D4FF", airy: "#F4F1FF", cream: "#F9F7FF" },
  text: { primary: "#1E1E1E", secondary: "#4B4B4B", tertiary: "#6F6F6F", quaternary: "#999999" },
};

export type ThemeColor = { p: string; s: string; soft: string; airy: string; cream?: string };

export const iconSize = { nav: 40, tab: 30, btn: 30, card: 36 };

export const navColors: Record<string, { light: string; dark: string; text: string }> = {
  overall: { light: "#FF8A6A", dark: "#FF6B4A", text: "#fff" },
  career:  { light: "#9BDFFD", dark: "#7DD3FC", text: "#1A5A7A" },
  love:    { light: "#FFCBDD", dark: "#FFB8D0", text: "#8A4A5A" },
  wealth:  { light: "#F7E36B", dark: "#F2D94D", text: "#5A4A10" },
  study:   { light: "#9BE8CF", dark: "#7DDFBD", text: "#2A5A4A" },
  social:  { light: "#CBBAFE", dark: "#B8A4FF", text: "#4A3A6A" },
};

export const categories = [
  { key: "overall", icon: "/icons/tile_1_nobg.png", theme: T.coral },
  { key: "career", icon: "/icons/tile_2_nobg.png", theme: T.career },
  { key: "love", icon: "/icons/tile_3_nobg.png", theme: T.love },
  { key: "wealth", icon: "/icons/tile_4_nobg.png", theme: T.wealth },
  { key: "study", icon: "/icons/tile_5_nobg.png", theme: T.study },
  { key: "social", icon: "/icons/tile_6_nobg.png", theme: T.social },
];

export const suggestedQuestions: Record<string, string[]> = {
  overall: ["Is today good for big decisions?", "What should I focus on?", "Should I start something new?", "How to make the most of today?", "What's my energy peak?"],
  career: ["Should I bring up the promotion?", "Best time for presentations?", "When to schedule the meeting?", "Take on more responsibility?", "How to impress my boss?"],
  love: ["Should I reach out first?", "Good day for the big talk?", "How to deepen the connection?", "Give them space today?", "Is romance in the air?"],
  wealth: ["Good day for investments?", "Should I make the purchase?", "When does financial luck peak?", "Budget meeting approach?", "Side hustle energy today?"],
  study: ["Best study time today?", "Start the new course now?", "How to improve focus?", "Good day for creative work?", "Exam prep strategy?"],
  social: ["Attend the event tonight?", "Good day for networking?", "Handle this conflict how?", "Who to reconnect with?", "Party or stay in?"],
};

export const candyColors: Record<string, { light: string; dark: string; shadow: string; text: string }> = {
  overall: { light: "#FF8A6A", dark: "#FF6B4A", shadow: "#FF6B4A", text: "#fff" },
  career:  { light: "#9BDFFD", dark: "#7DD3FC", shadow: "#7DD3FC", text: "#1A5A7A" },
  love:    { light: "#FFCBDD", dark: "#FFB8D0", shadow: "#E8A0B8", text: "#5A3A4A" },
  wealth:  { light: "#F7E36B", dark: "#F2D94D", shadow: "#E8C24A", text: "#5A4A20" },
  study:   { light: "#9BE8CF", dark: "#7DDFBD", shadow: "#6AC8A8", text: "#2A4A3A" },
  social:  { light: "#CBBAFE", dark: "#B8A4FF", shadow: "#A090E8", text: "#3A3050" },
  diary:   { light: "#7AA3FF", dark: "#5C8BFF", shadow: "#5C8BFF", text: "#fff" },
  purple:  { light: "#8F6BF7", dark: "#7A55E8", shadow: "#7A55E8", text: "#fff" },
  honey:   { light: "#FFE073", dark: "#FFD75A", shadow: "#E8C24A", text: "#5A4A20" },
};
