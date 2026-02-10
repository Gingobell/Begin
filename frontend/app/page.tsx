"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "./i18n";

type AuthMode = "login" | "signup";
type QuestionType = "input" | "date" | "single" | "multi";
type FlowAnswerValue = string | string[];

type FlowOption = {
  value: string;
  label: string;
};

type FlowQuestion = {
  id: string;
  type: QuestionType;
  prompt: string;
  help?: string;
  placeholder?: string;
  options?: FlowOption[];
  optional?: boolean;
  required?: boolean;
};


const baseSequence = ["name", "gender", "birthday", "region", "status"];
const studentSequence = ["name", "gender", "birthday", "region", "status", "student_industry", "student_focus", "relationship_student"];
const workingSequence = [
  "name",
  "gender",
  "birthday",
  "region",
  "status",
  "work_type",
  "industry",
  "role",
  "rhythm",
  "relationship_working",
  "income",
];

function getNextQuestionId(id: string, answers: Record<string, FlowAnswerValue>): string | null {
  switch (id) {
    case "name":
      return "gender";
    case "gender":
      return "birthday";
    case "birthday":
      return "region";
    case "region":
      return "status";
    case "status":
      return answers.status === "student" ? "student_industry" : "work_type";
    case "student_industry":
      return "student_focus";
    case "student_focus":
      return "relationship_student";
    case "relationship_student":
      return null;
    case "work_type":
      return "industry";
    case "industry":
      return "role";
    case "role":
      return "rhythm";
    case "rhythm":
      return "relationship_working";
    case "relationship_working":
      return "income";
    case "income":
      return null;
    default:
      return null;
  }
}

export default function LandingPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const landingRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const authTimerRef = useRef<number | null>(null);
  const flowTimerRef = useRef<number | null>(null);

  const [navScrolled, setNavScrolled] = useState(false);

  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authSuccess, setAuthSuccess] = useState("");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");

  const [profileOpen, setProfileOpen] = useState(false);
  const [flowCurrentId, setFlowCurrentId] = useState("name");
  const [flowHistory, setFlowHistory] = useState<string[]>([]);
  const [flowAnswers, setFlowAnswers] = useState<Record<string, FlowAnswerValue>>({});
  const [flowError, setFlowError] = useState("");
  const [flowComplete, setFlowComplete] = useState(false);


  const activeSequence = useMemo(() => {
    if (flowAnswers.status === "student") return studentSequence;
    if (flowAnswers.status === "working") return workingSequence;
    return baseSequence;
  }, [flowAnswers.status]);

  const questions: Record<string, FlowQuestion> = useMemo(() => ({
    name: {
      id: "name",
      type: "input",
      prompt: t("onboarding.name.prompt"),
      help: t("onboarding.name.help"),
      placeholder: t("onboarding.name.placeholder"),
      required: true,
    },
    gender: {
      id: "gender",
      type: "single",
      prompt: t("onboarding.gender.prompt"),
      options: [
        { value: "male", label: t("onboarding.gender.male") },
        { value: "female", label: t("onboarding.gender.female") },
        { value: "other", label: t("onboarding.gender.other") },
      ],
      required: true,
    },
    birthday: {
      id: "birthday",
      type: "date",
      prompt: t("onboarding.birthday.prompt"),
      help: t("onboarding.birthday.help"),
      required: true,
    },
    region: {
      id: "region",
      type: "single",
      prompt: t("onboarding.region.prompt"),
      options: [
        { value: "china", label: t("onboarding.region.china") },
        { value: "usa", label: t("onboarding.region.usa") },
        { value: "canada", label: t("onboarding.region.canada") },
        { value: "other", label: t("onboarding.region.other") },
      ],
      required: true,
    },
    status: {
      id: "status",
      type: "single",
      prompt: t("onboarding.status.prompt"),
      options: [
        { value: "student", label: t("onboarding.status.student") },
        { value: "working", label: t("onboarding.status.working") },
      ],
      required: true,
    },
    student_industry: {
      id: "student_industry",
      type: "multi",
      prompt: t("onboarding.studentIndustry.prompt"),
      options: [
        { value: "tech", label: t("onboarding.studentIndustry.tech") },
        { value: "finance", label: t("onboarding.studentIndustry.finance") },
        { value: "creative", label: t("onboarding.studentIndustry.creative") },
        { value: "edu", label: t("onboarding.studentIndustry.edu") },
        { value: "unsure", label: t("onboarding.studentIndustry.unsure") },
      ],
      required: true,
    },
    student_focus: {
      id: "student_focus",
      type: "multi",
      prompt: t("onboarding.studentFocus.prompt"),
      options: [
        { value: "study", label: t("onboarding.studentFocus.study") },
        { value: "job", label: t("onboarding.studentFocus.job") },
        { value: "skill", label: t("onboarding.studentFocus.skill") },
        { value: "network", label: t("onboarding.studentFocus.network") },
        { value: "balance", label: t("onboarding.studentFocus.balance") },
        { value: "explore", label: t("onboarding.studentFocus.explore") },
      ],
      required: true,
    },
    relationship_student: {
      id: "relationship_student",
      type: "multi",
      prompt: t("onboarding.relationship.prompt"),
      help: t("onboarding.relationship.help"),
      options: [
        { value: "single", label: t("onboarding.relationship.single") },
        { value: "dating", label: t("onboarding.relationship.dating") },
        { value: "partnered", label: t("onboarding.relationship.partnered") },
        { value: "complex", label: t("onboarding.relationship.complex") },
      ],
      optional: true,
      required: false,
    },
    work_type: {
      id: "work_type",
      type: "multi",
      prompt: t("onboarding.workType.prompt"),
      options: [
        { value: "fulltime", label: t("onboarding.workType.fulltime") },
        { value: "parttime", label: t("onboarding.workType.parttime") },
        { value: "freelance", label: t("onboarding.workType.freelance") },
        { value: "startup", label: t("onboarding.workType.startup") },
      ],
      required: true,
    },
    industry: {
      id: "industry",
      type: "multi",
      prompt: t("onboarding.industry.prompt"),
      options: [
        { value: "tech", label: t("onboarding.industry.tech") },
        { value: "finance", label: t("onboarding.industry.finance") },
        { value: "creative", label: t("onboarding.industry.creative") },
        { value: "edu", label: t("onboarding.industry.edu") },
        { value: "other", label: t("onboarding.industry.other") },
      ],
      required: true,
    },
    role: {
      id: "role",
      type: "multi",
      prompt: t("onboarding.role.prompt"),
      options: [
        { value: "engineer", label: t("onboarding.role.engineer") },
        { value: "product", label: t("onboarding.role.product") },
        { value: "design", label: t("onboarding.role.design") },
        { value: "marketing", label: t("onboarding.role.marketing") },
        { value: "sales", label: t("onboarding.role.sales") },
        { value: "admin", label: t("onboarding.role.admin") },
        { value: "other", label: t("onboarding.role.other") },
      ],
      required: true,
    },
    rhythm: {
      id: "rhythm",
      type: "multi",
      prompt: t("onboarding.rhythm.prompt"),
      options: [
        { value: "remote", label: t("onboarding.rhythm.remote") },
        { value: "onsite", label: t("onboarding.rhythm.onsite") },
        { value: "hybrid", label: t("onboarding.rhythm.hybrid") },
        { value: "travel", label: t("onboarding.rhythm.travel") },
      ],
      required: true,
    },
    relationship_working: {
      id: "relationship_working",
      type: "multi",
      prompt: t("onboarding.relationship.prompt"),
      help: t("onboarding.relationship.help"),
      options: [
        { value: "single", label: t("onboarding.relationship.single") },
        { value: "dating", label: t("onboarding.relationship.dating") },
        { value: "partnered", label: t("onboarding.relationship.partnered") },
        { value: "complex", label: t("onboarding.relationship.complex") },
      ],
      optional: true,
      required: false,
    },
    income: {
      id: "income",
      type: "multi",
      prompt: t("onboarding.income.prompt"),
      help: t("onboarding.income.help"),
      options: [
        { value: "salary", label: t("onboarding.income.salary") },
        { value: "bonus", label: t("onboarding.income.bonus") },
        { value: "invest", label: t("onboarding.income.invest") },
        { value: "side", label: t("onboarding.income.side") },
        { value: "other", label: t("onboarding.income.other") },
      ],
      optional: true,
      required: false,
    },
  }), [t]);

  const currentQuestion = questions[flowCurrentId];
  const step = flowComplete ? activeSequence.length : Math.max(activeSequence.indexOf(flowCurrentId) + 1, 1);
  const total = activeSequence.length;
  const nextQuestionId = flowComplete ? null : getNextQuestionId(flowCurrentId, flowAnswers);

  const flowQuestionTag = flowComplete ? t("common.done") : `Q${step} · ${currentQuestion?.id || "question"}`;
  const flowPrompt = flowComplete ? t("landing.profileComplete") : currentQuestion?.prompt || "";
  const flowHelp = flowComplete ? t("landing.profileCompleteHelp") : currentQuestion?.help || "";
  const flowProgress = Math.round(((flowComplete ? total : step) / Math.max(total, 1)) * 100);

  useEffect(() => {
    const scroller = landingRef.current;
    if (!scroller) return;

    const handleScroll = () => {
      setNavScrolled(scroller.scrollTop > 40);
    };

    scroller.addEventListener("scroll", handleScroll, { passive: true });
    return () => scroller.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.2, rootMargin: "0px 0px -20px 0px", root: landingRef.current },
    );

    const targets = Array.from(document.querySelectorAll(".fade-in,.fade-in-stagger"));
    targets.forEach((node) => observer.observe(node));

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!authOpen) return;

    const timer = window.setTimeout(() => {
      const targetId = authMode === "signup" ? "signupName" : "loginEmail";
      const target = document.getElementById(targetId) as HTMLInputElement | null;
      target?.focus();
    }, 280);

    return () => window.clearTimeout(timer);
  }, [authOpen, authMode]);

  useEffect(() => {
    document.body.classList.toggle("flow-open", profileOpen);
    return () => document.body.classList.remove("flow-open");
  }, [profileOpen]);

useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;

      if (profileOpen) {
        setProfileOpen(false);
        setFlowError("");
        return;
      }

      if (authOpen) {
        setAuthOpen(false);
        setAuthSuccess("");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [authOpen, profileOpen]);

  useEffect(() => {
    return () => {
      if (authTimerRef.current) {
        window.clearTimeout(authTimerRef.current);
      }
      if (flowTimerRef.current) {
        window.clearTimeout(flowTimerRef.current);
      }
    };
  }, []);

  const closeAuthPanel = () => {
    if (authTimerRef.current) {
      window.clearTimeout(authTimerRef.current);
      authTimerRef.current = null;
    }
    setAuthOpen(false);
    setAuthSuccess("");
  };

  const closeProfileFlow = () => {
    if (flowTimerRef.current) {
      window.clearTimeout(flowTimerRef.current);
      flowTimerRef.current = null;
    }
    setProfileOpen(false);
    setFlowError("");
  };

  const openAuth = (mode: AuthMode) => {
    setAuthMode(mode);
    setAuthSuccess("");
    setAuthOpen(true);
    heroRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const openProfileFlow = (preset: { name?: string; email?: string } = {}) => {
    if (flowTimerRef.current) {
      window.clearTimeout(flowTimerRef.current);
      flowTimerRef.current = null;
    }

    setFlowCurrentId("name");
    setFlowHistory([]);
    setFlowAnswers({
      name: preset.name || "",
      email: preset.email || "",
    });
    setFlowError("");
    setFlowComplete(false);
    setProfileOpen(true);
  };

  const setFlowAnswer = (id: string, value: FlowAnswerValue) => {
    setFlowAnswers((prev) => ({ ...prev, [id]: value }));
  };

  const validateCurrentQuestion = () => {
    if (flowComplete || !currentQuestion) return true;

    const value = flowAnswers[currentQuestion.id];
    if (currentQuestion.required === false) return true;

    if (currentQuestion.type === "input" || currentQuestion.type === "date") {
      if (typeof value !== "string" || !value.trim()) {
        setFlowError(t("landing.pleaseFillin"));
        return false;
      }
      return true;
    }

    if (currentQuestion.type === "single") {
      if (typeof value !== "string" || !value) {
        setFlowError(t("landing.pleaseChooseOne"));
        return false;
      }
      return true;
    }

    if (currentQuestion.type === "multi") {
      const selected = Array.isArray(value) ? value : [];
      if (selected.length === 0) {
        setFlowError(t("landing.pleaseSelectOne"));
        return false;
      }
      return true;
    }

    return true;
  };

  const completeFlow = () => {
    try {
      localStorage.setItem(
        "beginProfile",
        JSON.stringify({
          ...flowAnswers,
          completedAt: new Date().toISOString(),
        }),
      );
    } catch {
      // Ignore storage errors to avoid blocking the core flow.
    }

    setFlowComplete(true);
    setFlowError("");

    if (flowTimerRef.current) {
      window.clearTimeout(flowTimerRef.current);
    }

    flowTimerRef.current = window.setTimeout(() => {
      closeProfileFlow();
    }, 700);
  };

  const goNextFlow = () => {
    if (!validateCurrentQuestion()) return;

    setFlowError("");

    const nextId = getNextQuestionId(flowCurrentId, flowAnswers);
    if (!nextId) {
      completeFlow();
      return;
    }

    setFlowHistory((prev) => [...prev, flowCurrentId]);
    setFlowCurrentId(nextId);
  };

  const goBackFlow = () => {
    if (flowHistory.length === 0) return;

    const nextHistory = [...flowHistory];
    const previousId = nextHistory.pop();

    if (!previousId) return;

    setFlowHistory(nextHistory);
    setFlowCurrentId(previousId);
    setFlowComplete(false);
    setFlowError("");
  };

  const skipCurrentFlow = () => {
    if (!currentQuestion?.optional) return;

    setFlowAnswer(currentQuestion.id, []);
    setFlowError("");

    const nextId = getNextQuestionId(currentQuestion.id, flowAnswers);
    if (!nextId) {
      completeFlow();
      return;
    }

    setFlowHistory((prev) => [...prev, currentQuestion.id]);
    setFlowCurrentId(nextId);
  };

  const toggleFlowOption = (optionValue: string) => {
    if (!currentQuestion) return;

    const currentValue = flowAnswers[currentQuestion.id];

    if (currentQuestion.type === "single") {
      setFlowAnswer(currentQuestion.id, optionValue);
      setFlowError("");
      return;
    }

    const existing = Array.isArray(currentValue) ? [...currentValue] : [];
    const existingIndex = existing.indexOf(optionValue);

    if (existingIndex >= 0) {
      existing.splice(existingIndex, 1);
    } else {
      existing.push(optionValue);
    }

    setFlowAnswer(currentQuestion.id, existing);
    setFlowError("");
  };

  const handleLoginSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    setAuthSuccess(t("auth.loginSuccess"));

    if (authTimerRef.current) {
      window.clearTimeout(authTimerRef.current);
    }

    authTimerRef.current = window.setTimeout(() => {
      closeAuthPanel();
      router.push("/home");
    }, 420);
  };

  const handleSignupSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    setAuthSuccess(t("auth.signupSuccess"));

    if (authTimerRef.current) {
      window.clearTimeout(authTimerRef.current);
    }

    authTimerRef.current = window.setTimeout(() => {
      openProfileFlow({ name: signupName.trim(), email: signupEmail.trim() });
    }, 380);
  };

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  const selectedValues = useMemo(() => {
    if (!currentQuestion) return new Set<string>();

    const currentValue = flowAnswers[currentQuestion.id];
    if (Array.isArray(currentValue)) {
      return new Set<string>(currentValue);
    }

    if (typeof currentValue === "string" && currentValue) {
      return new Set<string>([currentValue]);
    }

    return new Set<string>();
  }, [currentQuestion, flowAnswers]);

  return (
    <div ref={landingRef} className="landing-scroll">
      <div className="orb-container">
        <div className="orb orb--coral-1" />
        <div className="orb orb--coral-2" />
        <div className="orb orb--coral-3" />
        <div className="orb orb--blue-1" />
        <div className="orb orb--blue-2" />
        <div className="orb orb--honey" />
        <div className="orb orb--purple" />
      </div>

      <div className="page-wrapper">
        <nav className={`nav ${navScrolled ? "nav--scrolled" : ""}`} id="nav">
          <div className="container">
            <a
              href="#"
              className="nav__logo"
              onClick={(event) => {
                event.preventDefault();
                landingRef.current?.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              <img src="/logo.png" alt="Begin" />
              <span>Begin</span>
            </a>

            <div className="nav__links">
              <a
                href="#different"
                className="nav__link"
                onClick={(event) => {
                  event.preventDefault();
                  scrollToSection("different");
                }}
              >
                {t("landing.whyBegin")}
              </a>
              <a
                href="#action"
                className="nav__link"
                onClick={(event) => {
                  event.preventDefault();
                  scrollToSection("action");
                }}
              >
                {t("landing.seeItWork")}
              </a>
              <a
                href="#engine"
                className="nav__link"
                onClick={(event) => {
                  event.preventDefault();
                  scrollToSection("engine");
                }}
              >
                {t("landing.howItWorks")}
              </a>
              <button
                className="candy-btn candy-btn--coral"
                type="button"
                style={{ padding: "10px 24px", fontSize: 13 }}
                onClick={() => openAuth("signup")}
              >
                {t("landing.getStarted")}
              </button>
            </div>
          </div>
        </nav>

        <section ref={heroRef} className={`page hero ${authOpen ? "hero--auth-open" : ""}`}>
          <div className="container">
            <div className="hero__stage">
              <div className="hero__content">
                <h1 className="hero__title">
                  {t("landing.heroTitle")}
                  <br />
                  <em>
                    {t("landing.heroSubtitleEm").split("\n")[0]}
                    <br />
                    {t("landing.heroSubtitleEm").split("\n")[1]}
                  </em>
                </h1>
                <p className="hero__subtitle">{t("landing.heroDesc")}</p>
                <div className="hero__actions">
                  <button className="candy-btn candy-btn--coral" type="button" onClick={() => openAuth("login")}>
                    {t("auth.logInSignUp")}
                  </button>
                  <button className="glass-btn" type="button" onClick={() => scrollToSection("different")}>
                    {t("landing.learnMore")}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="page different" id="different">
          <div className="container">
            <div className="fade-in">
              <div className="section-label">{t("landing.differentLabel")}</div>
              <h2 className="section-title">{t("landing.differentTitle")}</h2>
            </div>

            <div className="compare-duo fade-in">
              <div className="compare-card compare-card--other">
                <div className="compare-card__label">{t("landing.otherApps")}</div>
                <div className="compare-card__text">{t("landing.otherAppsText")}</div>
              </div>
              <div className="compare-card compare-card--begin">
                <div className="compare-card__label">{t("landing.beginLabel")}</div>
                <div className="compare-card__text" dangerouslySetInnerHTML={{ __html: t("landing.beginText") }} />
              </div>
            </div>

            <div className="section-quote fade-in" dangerouslySetInnerHTML={{ __html: t("landing.sectionQuote") }} />
          </div>
        </section>

        <section className="page action" id="action">
          <div className="container">
            <div className="fade-in" style={{ marginBottom: 32 }}>
              <div className="section-label">{t("landing.actionLabel")}</div>
              <h2 className="section-title">
                {t("landing.actionTitle").split("\n")[0]}
                <br />
                {t("landing.actionTitle").split("\n")[1]}
              </h2>
            </div>

            <div className="action-body fade-in">
              <div className="timeline">
                <div className="timeline__line" />

                <div className="timeline__node">
                  <div className="timeline__dot" />
                  <div className="timeline__time">{t("landing.timelineTime1")}</div>
                  <div className="timeline__card">
                    <strong>{t("landing.timelineYouWrote")}</strong>
                    {t("landing.timelineYouWroteText")}
                  </div>
                </div>

                <div className="timeline__node">
                  <div className="timeline__dot" />
                  <div className="timeline__time">{t("landing.timelineTime2")}</div>
                  <div className="timeline__card">
                    <strong>{t("landing.timelineBeginSays")}</strong>
                    {t("landing.communication")} <span className="stars">★★★★★</span>
                    <br />
                    {t("landing.timelineBeginSaysText")}
                  </div>
                </div>

                <div className="timeline__node">
                  <div className="timeline__dot" />
                  <div className="timeline__time">{t("landing.timelineTime3")}</div>
                  <div className="timeline__card">
                    <strong>{t("landing.timelineYouWroteBack")}</strong>
                    {t("landing.timelineYouWroteBackText")}
                  </div>
                </div>
              </div>

              <div className="action-aside">
                <div className="action-aside__title">{t("landing.just90Seconds")}</div>
                <div className="action-aside__sub">{t("landing.thatsAllItTakes")}</div>

                <div className="time-capsule time-capsule--morning">
                  <div className="time-capsule__glow">AM</div>
                  <div className="time-capsule__info">
                    <div className="time-capsule__label">{t("landing.morningLabel")}</div>
                    <div className="time-capsule__desc">{t("landing.morningDesc")}</div>
                  </div>
                </div>

                <div className="time-capsule time-capsule--evening">
                  <div className="time-capsule__glow">PM</div>
                  <div className="time-capsule__info">
                    <div className="time-capsule__label">{t("landing.eveningLabel")}</div>
                    <div className="time-capsule__desc">{t("landing.eveningDesc")}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="page engine" id="engine">
          <div className="container">
            <div className="fade-in" style={{ marginBottom: 32 }}>
              <div className="section-label">{t("landing.engineLabel")}</div>
              <h2 className="section-title">{t("landing.engineTitle")}</h2>
              <p style={{ fontSize: 16, color: "var(--text-secondary)", maxWidth: 500, margin: "0 auto" }}>
                {t("landing.engineDesc")}
              </p>
            </div>

            <div className="growth-row fade-in-stagger">
              <div className="growth-card">
                <div className="growth-card__glow" />
                <div className="growth-card__dot" />
                <div className="growth-card__phase">{t("landing.day1Phase")}</div>
                <div className="growth-card__title">{t("landing.day1Title")}</div>
                <div className="growth-card__desc">{t("landing.day1Desc")}</div>
                <div className="growth-card__quote">{t("landing.day1Quote")}</div>
              </div>

              <div className="growth-card">
                <div className="growth-card__glow" />
                <div className="growth-card__dot" />
                <div className="growth-card__phase">{t("landing.day2Phase")}</div>
                <div className="growth-card__title">{t("landing.day2Title")}</div>
                <div className="growth-card__desc">{t("landing.day2Desc")}</div>
                <div className="growth-card__quote">{t("landing.day2Quote")}</div>
              </div>

              <div className="growth-card">
                <div className="growth-card__glow" />
                <div className="growth-card__dot" />
                <div className="growth-card__phase">{t("landing.day5Phase")}</div>
                <div className="growth-card__title">{t("landing.day5Title")}</div>
                <div className="growth-card__desc">{t("landing.day5Desc")}</div>
                <div className="growth-card__quote">{t("landing.day5Quote")}</div>
              </div>
            </div>
          </div>
        </section>

        <section className="page cta">
          <div className="container">
            <div className="fade-in">
              <h2 className="cta__title">
                {t("landing.ctaTitle").split("\n")[0]}
                <br />
                {t("landing.ctaTitle").split("\n")[1]}
              </h2>
              <p className="cta__desc">{t("landing.ctaDesc")}</p>
              <button
                className="candy-btn candy-btn--coral"
                type="button"
                style={{ fontSize: 17, padding: "18px 48px" }}
                onClick={() => openAuth("signup")}
              >
                {t("landing.ctaButton")}
              </button>
              <div className="cta__tagline">{t("landing.ctaTagline")}</div>
            </div>
          </div>
        </section>

        <div
          className={`auth-overlay ${authOpen ? "is-open" : ""}`}
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closeAuthPanel();
            }
          }}
        >
          <aside className="auth-panel" id="authPanel" aria-live="polite">
            <div className="auth-shell">
              <div className="auth-head">
                <div>
                  <h3 className="auth-title">{t("auth.welcomeTitle")}</h3>
                  <p className="auth-subtitle">{t("auth.welcomeSubtitle")}</p>
                </div>
                <button className="auth-close" type="button" aria-label="Close" onClick={closeAuthPanel}>
                  ×
                </button>
              </div>

              <div className="auth-tabs" role="tablist" aria-label="Auth mode">
                <button
                  className={`auth-tab ${authMode === "login" ? "is-active" : ""}`}
                  data-tab="login"
                  type="button"
                  aria-selected={authMode === "login"}
                  onClick={() => {
                    setAuthMode("login");
                    setAuthSuccess("");
                  }}
                >
                  {t("auth.logIn")}
                </button>
                <button
                  className={`auth-tab ${authMode === "signup" ? "is-active" : ""}`}
                  data-tab="signup"
                  type="button"
                  aria-selected={authMode === "signup"}
                  onClick={() => {
                    setAuthMode("signup");
                    setAuthSuccess("");
                  }}
                >
                  {t("auth.signUp")}
                </button>
              </div>

              <form className={`auth-form ${authMode === "login" ? "is-active" : ""}`} id="loginForm" onSubmit={handleLoginSubmit}>
                <div className="auth-field">
                  <label htmlFor="loginEmail">{t("auth.email")}</label>
                  <input
                    id="loginEmail"
                    type="email"
                    name="email"
                    placeholder="you@begin.com"
                    required
                    value={loginEmail}
                    onChange={(event) => setLoginEmail(event.target.value)}
                  />
                </div>

                <div className="auth-field">
                  <label htmlFor="loginPassword">{t("auth.password")}</label>
                  <input
                    id="loginPassword"
                    type="password"
                    name="password"
                    placeholder={t("auth.passwordHint")}
                    minLength={6}
                    required
                    value={loginPassword}
                    onChange={(event) => setLoginPassword(event.target.value)}
                  />
                </div>

                <div className="form-foot">
                  <span className="hint">{t("auth.loginHint")}</span>
                  <button
                    className="link-btn"
                    type="button"
                    onClick={() => {
                      setAuthMode("signup");
                      setAuthSuccess("");
                    }}
                  >
                    {t("auth.needAccount")}
                  </button>
                </div>

                <button className="auth-submit" type="submit">
                  {t("auth.loginAndContinue")}
                </button>
              </form>

              <form className={`auth-form ${authMode === "signup" ? "is-active" : ""}`} id="signupForm" onSubmit={handleSignupSubmit}>
                <div className="auth-field">
                  <label htmlFor="signupName">{t("auth.name")}</label>
                  <input
                    id="signupName"
                    type="text"
                    name="name"
                    placeholder={t("onboarding.name.prompt")}
                    required
                    value={signupName}
                    onChange={(event) => setSignupName(event.target.value)}
                  />
                </div>

                <div className="auth-field">
                  <label htmlFor="signupEmail">{t("auth.email")}</label>
                  <input
                    id="signupEmail"
                    type="email"
                    name="email"
                    placeholder="you@begin.com"
                    required
                    value={signupEmail}
                    onChange={(event) => setSignupEmail(event.target.value)}
                  />
                </div>

                <div className="auth-field">
                  <label htmlFor="signupPassword">{t("auth.password")}</label>
                  <input
                    id="signupPassword"
                    type="password"
                    name="password"
                    placeholder={t("auth.passwordHint")}
                    minLength={6}
                    required
                    value={signupPassword}
                    onChange={(event) => setSignupPassword(event.target.value)}
                  />
                </div>

                <div className="form-foot">
                  <span className="hint">{t("auth.signupHint")}</span>
                  <button
                    className="link-btn"
                    type="button"
                    onClick={() => {
                      setAuthMode("login");
                      setAuthSuccess("");
                    }}
                  >
                    {t("auth.haveAccount")}
                  </button>
                </div>

                <button className="auth-submit" type="submit">
                  {t("auth.createAccount")}
                </button>
              </form>

              <div className={`auth-success ${authSuccess ? "show" : ""}`} role="status" aria-live="polite">
                {authSuccess}
              </div>
            </div>
          </aside>
        </div>

        <div className={`profile-flow ${profileOpen ? "is-open" : ""}`} aria-hidden={!profileOpen}>
          <div className="profile-flow__backdrop" />
          <div className="profile-flow__shell">
            <div className="phone-card">
              <div className="phone-notch" />

              <div className="flow-head">
                <div className="flow-head__text">
                  <h3>{t("landing.completeProfile")}</h3>
                  <small>{t("landing.profileSubtitle")}</small>
                </div>
                <button className="flow-close" type="button" aria-label="Close" onClick={closeProfileFlow}>
                  ×
                </button>
              </div>

              <div className="flow-meta">
                <div className="flow-meta__step">{t("landing.stepOf").replace("{step}", String(flowComplete ? total : step)).replace("{total}", String(total))}</div>
                <div className="flow-progress">
                  <span style={{ width: `${flowProgress}%` }} />
                </div>
              </div>

              <div className="flow-body">
                <div className="flow-question">{flowQuestionTag}</div>
                <div className="flow-prompt">{flowPrompt}</div>
                <div className="flow-help">{flowHelp}</div>

                <div id="flowInputArea">
                  {!flowComplete && currentQuestion && (currentQuestion.type === "input" || currentQuestion.type === "date") && (
                    <input
                      className="flow-input"
                      type={currentQuestion.type === "date" ? "date" : "text"}
                      placeholder={currentQuestion.placeholder || ""}
                      value={typeof flowAnswers[currentQuestion.id] === "string" ? (flowAnswers[currentQuestion.id] as string) : ""}
                      onChange={(event) => {
                        setFlowAnswer(currentQuestion.id, event.target.value);
                        setFlowError("");
                      }}
                      autoComplete="off"
                    />
                  )}

                  {!flowComplete && currentQuestion && (currentQuestion.type === "single" || currentQuestion.type === "multi") && (
                    <div className="option-grid">
                      {currentQuestion.options?.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          className={`option-btn ${selectedValues.has(option.value) ? "is-selected" : ""}`}
                          onClick={() => toggleFlowOption(option.value)}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flow-error">{flowError}</div>

                <button className="flow-skip" type="button" hidden={flowComplete || !currentQuestion?.optional} onClick={skipCurrentFlow}>
                  {t("landing.skipQuestion")}
                </button>

                <div className="flow-actions">
                  {!flowComplete && (
                    <button className="flow-btn flow-btn--ghost" type="button" onClick={goBackFlow} disabled={flowHistory.length === 0}>
                      {t("common.back")}
                    </button>
                  )}
                  {!flowComplete && (
                    <button className="flow-btn flow-btn--primary" type="button" onClick={goNextFlow}>
                      {nextQuestionId ? t("common.next") : t("common.finish")}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <style jsx global>{`
        :root {
          --cream: #fdfbf8;
          --coral-primary: #ff6b4a;
          --coral-secondary: #ff8a6a;
          --coral-soft: #ffb89a;
          --coral-airy: #fff5f0;
          --blue-primary: #5c8bff;
          --blue-soft: #a8c4ff;
          --honey-primary: #ffd75a;
          --purple-light: #8f6bf7;
          --purple-soft: #d4c5ff;
          --text-primary: #1e1e1e;
          --text-secondary: #4b4b4b;
          --text-tertiary: #6f6f6f;
          --text-quaternary: #999999;
          --glass-bg: rgba(255, 255, 255, 0.82);
          --glass-border: rgba(255, 255, 255, 0.55);
        }

        .landing-scroll * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        .landing-scroll {
          height: 100vh;
          font-family: "DM Sans", -apple-system, sans-serif;
          background: var(--cream);
          color: var(--text-primary);
          overflow-x: hidden;
          overflow-y: auto;
          line-height: 1.6;
          scroll-snap-type: y mandatory;
          scroll-behavior: smooth;
          position: relative;
          -webkit-font-smoothing: antialiased;
        }

        .orb-container {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 0;
          overflow: hidden;
        }

        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          will-change: transform;
          animation: orbFloat 20s ease-in-out infinite;
        }

        .orb--coral-1 {
          width: 400px;
          height: 400px;
          background: rgba(255, 107, 74, 0.35);
          top: -120px;
          left: -80px;
          animation-duration: 22s;
        }

        .orb--coral-2 {
          width: 300px;
          height: 300px;
          background: rgba(255, 138, 106, 0.28);
          top: -60px;
          right: -60px;
          animation-duration: 18s;
          animation-delay: -4s;
        }

        .orb--coral-3 {
          width: 350px;
          height: 350px;
          background: rgba(255, 184, 154, 0.22);
          bottom: 30%;
          left: 10%;
          animation-duration: 25s;
          animation-delay: -8s;
        }

        .orb--blue-1 {
          width: 320px;
          height: 320px;
          background: rgba(92, 139, 255, 0.3);
          top: 55%;
          right: -50px;
          animation-duration: 24s;
          animation-delay: -6s;
        }

        .orb--blue-2 {
          width: 250px;
          height: 250px;
          background: rgba(122, 163, 255, 0.2);
          bottom: 5%;
          left: -40px;
          animation-duration: 20s;
          animation-delay: -10s;
        }

        .orb--honey {
          width: 280px;
          height: 280px;
          background: rgba(255, 215, 90, 0.22);
          top: 40%;
          left: 50%;
          transform: translateX(-50%);
          animation-duration: 26s;
          animation-delay: -12s;
        }

        .orb--purple {
          width: 200px;
          height: 200px;
          background: rgba(143, 107, 247, 0.18);
          bottom: 20%;
          right: 15%;
          animation-duration: 19s;
          animation-delay: -3s;
        }

        .page-wrapper {
          position: relative;
          z-index: 1;
        }

        .page {
          height: 100vh;
          min-height: 100vh;
          max-height: 100vh;
          scroll-snap-align: start;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
        }

        .container {
          max-width: 1080px;
          margin: 0 auto;
          padding: 0 32px;
          width: 100%;
        }

        .candy-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 14px 36px;
          border: none;
          border-radius: 20px;
          font-family: "DM Sans", sans-serif;
          font-size: 15px;
          font-weight: 600;
          letter-spacing: 0.02em;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .candy-btn--coral {
          background: linear-gradient(to right, var(--coral-secondary), var(--coral-primary));
          color: white;
          box-shadow: 0 8px 24px rgba(255, 107, 74, 0.24);
        }

        .candy-btn--coral:hover {
          transform: scale(1.03);
          box-shadow: 0 12px 32px rgba(255, 107, 74, 0.32);
        }

        .candy-btn--coral:active {
          transform: scale(0.98);
        }

        .glass-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 12px 28px;
          background: rgba(255, 255, 255, 0.78);
          border: 1.5px solid rgba(255, 107, 74, 0.2);
          border-radius: 100px;
          font-family: "DM Sans", sans-serif;
          font-size: 14px;
          font-weight: 500;
          color: var(--coral-primary);
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        .glass-btn:hover {
          background: rgba(255, 255, 255, 0.92);
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        }

        .nav {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          z-index: 100;
          padding: 16px 0;
          transition: all 0.4s ease;
        }

        .nav--scrolled {
          background: rgba(253, 251, 248, 0.85);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.5);
          box-shadow: 0 2px 20px rgba(0, 0, 0, 0.04);
        }

        .nav .container {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .nav__logo {
          font-family: "Fraunces", serif;
          font-size: 24px;
          font-weight: 600;
          color: var(--text-primary);
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          gap: 10px;
        }

        .nav__logo img {
          width: 34px;
          height: 34px;
          border-radius: 11px;
          object-fit: cover;
        }

        .nav__links {
          display: flex;
          gap: 36px;
          align-items: center;
        }

        .nav__link {
          font-size: 14px;
          font-weight: 500;
          color: var(--text-secondary);
          text-decoration: none;
          transition: color 0.2s;
        }

        .nav__link:hover {
          color: var(--coral-primary);
        }

        .section-label {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--coral-primary);
          margin-bottom: 12px;
        }

        .section-title {
          font-family: "Fraunces", serif;
          font-size: clamp(28px, 3.5vw, 44px);
          font-weight: 500;
          line-height: 1.2;
          letter-spacing: -0.02em;
          margin-bottom: 16px;
        }

        .section-quote {
          font-family: "Fraunces", serif;
          font-size: 16px;
          font-style: italic;
          color: var(--text-tertiary);
          text-align: center;
          line-height: 1.6;
          max-width: 460px;
          margin: 0 auto;
        }

        .section-quote em {
          color: var(--coral-primary);
          font-weight: 500;
        }

        .hero {
          text-align: left;
        }

        .hero .container {
          display: block;
        }

        .hero__stage {
          display: grid;
          grid-template-columns: minmax(0, 760px);
          justify-content: center;
          justify-items: center;
          gap: 22px;
          align-items: center;
        }

        .hero__content {
          max-width: 760px;
          text-align: center;
          transition: transform 0.42s ease, opacity 0.42s ease;
        }

        .hero__title {
          font-family: "Fraunces", serif;
          font-size: clamp(40px, 5.2vw, 68px);
          font-weight: 500;
          line-height: 1.12;
          letter-spacing: -0.02em;
          color: var(--text-primary);
          margin-bottom: 20px;
          animation: fadeSlideUp 0.8s ease 0.1s both;
        }

        .hero__title em {
          font-style: italic;
          background: linear-gradient(135deg, var(--coral-primary), var(--purple-light));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .hero__subtitle {
          font-size: 18px;
          line-height: 1.7;
          color: var(--text-secondary);
          margin-bottom: 36px;
          max-width: 500px;
          animation: fadeSlideUp 0.8s ease 0.2s both;
        }

        .hero__actions {
          display: flex;
          gap: 16px;
          align-items: center;
          justify-content: center;
          animation: fadeSlideUp 0.8s ease 0.3s both;
        }

        .auth-overlay {
          position: fixed;
          inset: 0;
          z-index: 220;
          padding: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(253, 251, 248, 0.65);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          opacity: 0;
          pointer-events: none;
          transition: opacity 0.28s ease;
        }

        .auth-overlay.is-open {
          opacity: 1;
          pointer-events: auto;
        }

        .auth-panel {
          width: min(420px, 100%);
          opacity: 0;
          pointer-events: none;
          transform: translateY(14px) scale(0.98);
          transition: opacity 0.36s ease, transform 0.36s ease;
        }

        .auth-overlay.is-open .auth-panel {
          opacity: 1;
          pointer-events: auto;
          transform: translateY(0) scale(1);
        }

        .auth-shell {
          border-radius: 24px;
          padding: 22px;
          background:
            linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(255, 245, 240, 0.78)),
            radial-gradient(circle at 0 0, rgba(255, 184, 154, 0.25), transparent 55%);
          border: 1px solid rgba(255, 255, 255, 0.88);
          box-shadow:
            0 16px 46px rgba(255, 107, 74, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(20px);
          transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
        }

        .auth-shell:hover {
          transform: translateY(-4px);
          box-shadow:
            0 22px 56px rgba(255, 107, 74, 0.18),
            inset 0 1px 0 rgba(255, 255, 255, 0.92);
          border-color: rgba(255, 138, 106, 0.4);
        }

        .auth-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 14px;
        }

        .auth-title {
          font-family: "Fraunces", serif;
          font-size: 29px;
          line-height: 1.08;
        }

        .auth-subtitle {
          margin-top: 4px;
          font-size: 13px;
          color: var(--text-tertiary);
        }

        .auth-close {
          width: 34px;
          height: 34px;
          border: none;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.8);
          color: var(--text-tertiary);
          font-size: 20px;
          line-height: 1;
          cursor: pointer;
        }

        .auth-close:hover {
          color: var(--coral-primary);
        }

        .auth-tabs {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          padding: 5px;
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.62);
          border: 1px solid rgba(255, 255, 255, 0.72);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
          margin-bottom: 14px;
        }

        .auth-tab {
          border: none;
          border-radius: 10px;
          padding: 10px;
          background: transparent;
          color: var(--text-tertiary);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .auth-tab:hover {
          color: var(--coral-primary);
          background: rgba(255, 255, 255, 0.72);
        }

        .auth-tab.is-active {
          background: linear-gradient(135deg, var(--coral-secondary), var(--coral-primary));
          color: #fff;
        }

        .auth-form {
          display: none;
        }

        .auth-form.is-active {
          display: block;
        }

        .auth-field {
          margin-bottom: 10px;
        }

        .auth-field label {
          display: block;
          font-size: 12px;
          color: var(--text-tertiary);
          margin-bottom: 6px;
        }

        .auth-field input {
          width: 100%;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.9);
          background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(255, 245, 240, 0.74));
          padding: 11px 12px;
          font-family: inherit;
          font-size: 14px;
          color: var(--text-primary);
          transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
        }

        .auth-field input:hover {
          border-color: rgba(255, 138, 106, 0.36);
          transform: translateY(-1px);
        }

        .auth-field input:focus {
          outline: none;
          border-color: rgba(255, 107, 74, 0.42);
          box-shadow: 0 0 0 3px rgba(255, 107, 74, 0.12);
        }

        .form-foot {
          margin: 10px 0 14px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .hint {
          font-size: 12px;
          color: var(--text-quaternary);
        }

        .link-btn {
          border: none;
          background: transparent;
          color: var(--blue-primary);
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
        }

        .auth-submit {
          width: 100%;
          border: none;
          border-radius: 14px;
          padding: 12px 16px;
          font-family: "DM Sans", sans-serif;
          font-size: 14px;
          font-weight: 600;
          color: #fff;
          cursor: pointer;
          background: linear-gradient(135deg, var(--coral-secondary), var(--coral-primary));
          box-shadow: 0 8px 24px rgba(255, 107, 74, 0.22);
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .auth-submit:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 30px rgba(255, 107, 74, 0.3);
        }

        .auth-success {
          display: none;
          margin-top: 10px;
          padding: 9px 11px;
          border-radius: 10px;
          font-size: 12px;
          color: var(--blue-primary);
          background: rgba(92, 139, 255, 0.11);
          border: 1px solid rgba(92, 139, 255, 0.24);
        }

        .auth-success.show {
          display: block;
        }

        .different {
          text-align: center;
        }

        .compare-duo {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          max-width: 760px;
          margin: 0 auto 36px;
        }

        .compare-card {
          border-radius: 22px;
          padding: 32px 28px;
          display: flex;
          flex-direction: column;
          transition: transform 0.5s ease, box-shadow 0.5s ease;
        }

        .compare-card--other {
          background: rgba(240, 240, 238, 0.55);
          border: 1px solid rgba(0, 0, 0, 0.05);
        }

        .compare-card--other .compare-card__label {
          color: var(--text-quaternary);
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin-bottom: 14px;
        }

        .compare-card--other .compare-card__text {
          font-size: 17px;
          color: var(--text-tertiary);
          line-height: 1.55;
          font-family: "Fraunces", serif;
          font-weight: 400;
        }

        .compare-card--begin {
          background: var(--glass-bg);
          border: 1.5px solid rgba(255, 107, 74, 0.15);
          backdrop-filter: blur(20px);
          box-shadow: 0 12px 40px rgba(255, 107, 74, 0.08);
        }

        .compare-card--begin:hover {
          transform: translateY(-3px);
          box-shadow: 0 16px 48px rgba(255, 107, 74, 0.12);
        }

        .compare-card--begin .compare-card__label {
          color: var(--coral-primary);
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin-bottom: 14px;
        }

        .compare-card--begin .compare-card__text {
          font-size: 17px;
          color: var(--text-primary);
          line-height: 1.55;
          font-family: "Fraunces", serif;
          font-weight: 400;
        }

        .compare-card--begin .compare-card__text strong {
          color: var(--coral-primary);
          font-weight: 600;
        }

        .action {
          text-align: center;
        }

        .action-body {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 48px;
          align-items: center;
          max-width: 820px;
          margin: 0 auto;
        }

        .timeline {
          position: relative;
          padding-left: 40px;
        }

        .timeline__line {
          position: absolute;
          left: 14px;
          top: 12px;
          bottom: 12px;
          width: 2px;
          border-radius: 2px;
          background: linear-gradient(to bottom, var(--coral-soft), var(--coral-primary), var(--coral-soft));
        }

        .timeline__node {
          position: relative;
          text-align: left;
          padding: 8px 0 20px;
        }

        .timeline__node:last-child {
          padding-bottom: 0;
        }

        .timeline__dot {
          position: absolute;
          left: -32px;
          top: 14px;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: var(--coral-primary);
          border: 2.5px solid white;
          box-shadow: 0 0 0 2px var(--coral-primary), 0 2px 6px rgba(0, 0, 0, 0.1);
        }

        .timeline__time {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 6px;
          color: var(--coral-primary);
        }

        .timeline__card {
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          border-radius: 18px;
          padding: 16px 20px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
          font-size: 14px;
          line-height: 1.6;
          color: var(--text-secondary);
        }

        .timeline__card strong {
          display: block;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 3px;
          font-size: 14px;
        }

        .timeline__card .stars {
          color: var(--honey-primary);
          letter-spacing: 2px;
          font-size: 13px;
        }

        .action-aside {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .time-capsule {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 16px 24px;
          border-radius: 100px;
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
          transition: transform 0.4s ease;
        }

        .time-capsule:hover {
          transform: translateY(-2px);
        }

        .time-capsule__glow {
          width: 38px;
          height: 38px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.04em;
          position: relative;
          color: var(--text-secondary);
        }

        .time-capsule__glow::after {
          content: "";
          position: absolute;
          inset: -4px;
          border-radius: 50%;
          opacity: 0.4;
          animation: breathe 3s ease-in-out infinite;
        }

        .time-capsule--morning .time-capsule__glow::after {
          background: radial-gradient(circle, rgba(255, 107, 74, 0.3), transparent 70%);
        }

        .time-capsule--evening .time-capsule__glow::after {
          background: radial-gradient(circle, rgba(92, 139, 255, 0.3), transparent 70%);
          animation-delay: 1.5s;
        }

        .time-capsule__info {
          text-align: left;
        }

        .time-capsule__label {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .time-capsule__desc {
          font-size: 12px;
          color: var(--text-tertiary);
          margin-top: 1px;
        }

        .action-aside__title {
          font-family: "Fraunces", serif;
          font-size: 18px;
          font-weight: 500;
          color: var(--text-primary);
          text-align: center;
          margin-bottom: 4px;
        }

        .action-aside__sub {
          font-size: 13px;
          color: var(--text-tertiary);
          text-align: center;
        }

        .engine {
          text-align: center;
          position: relative;
          overflow: hidden;
        }

        .engine::before {
          content: "";
          position: absolute;
          top: -100px;
          left: -10%;
          right: -10%;
          bottom: -100px;
          background:
            radial-gradient(ellipse 600px 400px at 20% 30%, rgba(255, 184, 154, 0.12), transparent),
            radial-gradient(ellipse 500px 400px at 80% 60%, rgba(212, 197, 255, 0.12), transparent),
            radial-gradient(ellipse 400px 300px at 50% 80%, rgba(168, 196, 255, 0.08), transparent);
          pointer-events: none;
        }

        .engine .container {
          position: relative;
          z-index: 1;
        }

        .growth-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
          max-width: 900px;
          margin: 0 auto;
        }

        .growth-card {
          padding: 28px 24px;
          border-radius: 24px;
          text-align: left;
          background: var(--glass-bg);
          border: 1px solid var(--glass-border);
          backdrop-filter: blur(20px);
          box-shadow: 0 6px 24px rgba(0, 0, 0, 0.04);
          position: relative;
          overflow: hidden;
          transition: transform 0.5s ease, box-shadow 0.5s ease;
        }

        .growth-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.07);
        }

        .growth-card__glow {
          position: absolute;
          border-radius: 50%;
          filter: blur(50px);
          pointer-events: none;
          width: 120px;
          height: 120px;
          opacity: 0.35;
          top: -30px;
          right: -20px;
          transition: opacity 0.5s ease;
        }

        .growth-card:hover .growth-card__glow {
          opacity: 0.55;
        }

        .growth-card:nth-child(1) .growth-card__glow {
          background: rgba(255, 138, 106, 0.35);
        }

        .growth-card:nth-child(2) .growth-card__glow {
          background: rgba(92, 139, 255, 0.3);
        }

        .growth-card:nth-child(3) .growth-card__glow {
          background: rgba(143, 107, 247, 0.3);
        }

        .growth-card__dot {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          margin-bottom: 16px;
          position: relative;
          z-index: 1;
          animation: dotPulse 4s ease-in-out infinite;
        }

        .growth-card:nth-child(1) .growth-card__dot {
          background: radial-gradient(circle at 35% 35%, var(--coral-soft), var(--coral-primary));
          box-shadow: 0 4px 16px rgba(255, 107, 74, 0.25);
        }

        .growth-card:nth-child(2) .growth-card__dot {
          background: radial-gradient(circle at 35% 35%, var(--blue-soft), var(--blue-primary));
          box-shadow: 0 4px 16px rgba(92, 139, 255, 0.25);
          animation-delay: -1.3s;
        }

        .growth-card:nth-child(3) .growth-card__dot {
          background: radial-gradient(circle at 35% 35%, var(--purple-soft), var(--purple-light));
          box-shadow: 0 4px 16px rgba(143, 107, 247, 0.25);
          animation-delay: -2.6s;
        }

        .growth-card__phase {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin-bottom: 8px;
          position: relative;
          z-index: 1;
        }

        .growth-card:nth-child(1) .growth-card__phase {
          color: var(--coral-primary);
        }

        .growth-card:nth-child(2) .growth-card__phase {
          color: var(--blue-primary);
        }

        .growth-card:nth-child(3) .growth-card__phase {
          color: var(--purple-light);
        }

        .growth-card__title {
          font-family: "Fraunces", serif;
          font-size: 18px;
          font-weight: 500;
          color: var(--text-primary);
          margin-bottom: 8px;
          position: relative;
          z-index: 1;
        }

        .growth-card__desc {
          font-size: 13px;
          line-height: 1.6;
          color: var(--text-tertiary);
          margin-bottom: 14px;
          position: relative;
          z-index: 1;
        }

        .growth-card__quote {
          font-size: 14px;
          line-height: 1.55;
          font-style: italic;
          color: var(--text-secondary);
          padding: 12px 16px;
          border-radius: 14px;
          position: relative;
          z-index: 1;
        }

        .growth-card:nth-child(1) .growth-card__quote {
          background: rgba(255, 107, 74, 0.06);
          border-left: 2.5px solid var(--coral-soft);
        }

        .growth-card:nth-child(2) .growth-card__quote {
          background: rgba(92, 139, 255, 0.06);
          border-left: 2.5px solid var(--blue-soft);
        }

        .growth-card:nth-child(3) .growth-card__quote {
          background: rgba(143, 107, 247, 0.06);
          border-left: 2.5px solid var(--purple-soft);
        }

        .cta {
          text-align: center;
        }

        .cta__title {
          font-family: "Fraunces", serif;
          font-size: clamp(34px, 4.5vw, 52px);
          font-weight: 500;
          line-height: 1.2;
          margin-bottom: 18px;
        }

        .cta__desc {
          font-size: 17px;
          color: var(--text-secondary);
          margin-bottom: 36px;
          max-width: 460px;
          margin-left: auto;
          margin-right: auto;
          line-height: 1.7;
        }

        .cta__tagline {
          font-family: "Fraunces", serif;
          font-size: 16px;
          font-style: italic;
          color: var(--text-tertiary);
          margin-top: 40px;
        }

        body.flow-open {
          overflow: hidden;
        }

        .profile-flow {
          position: fixed;
          inset: 0;
          z-index: 260;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          opacity: 0;
          pointer-events: none;
          transition: opacity 0.28s ease;
        }

        .profile-flow.is-open {
          opacity: 1;
          pointer-events: auto;
        }

        .profile-flow__backdrop {
          position: absolute;
          inset: 0;
          background: rgba(253, 251, 248, 0.65);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
        }

        .profile-flow__shell {
          position: relative;
          width: min(420px, 100%);
        }

        .phone-card {
          position: relative;
          border-radius: 34px;
          padding: 20px 18px 18px;
          background:
            linear-gradient(150deg, rgba(255, 255, 255, 0.94), rgba(255, 245, 240, 0.86)),
            radial-gradient(circle at 100% 0, rgba(255, 184, 154, 0.2), transparent 45%);
          border: 1px solid rgba(255, 255, 255, 0.9);
          box-shadow:
            0 24px 56px rgba(48, 48, 48, 0.18),
            0 0 0 8px rgba(255, 255, 255, 0.3);
        }

        .phone-notch {
          width: 40%;
          min-width: 148px;
          height: 24px;
          margin: 0 auto 14px;
          border-radius: 999px;
          background: linear-gradient(145deg, rgba(36, 36, 36, 0.96), rgba(62, 62, 62, 0.9));
        }

        .flow-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 10px;
        }

        .flow-head__text small {
          display: block;
          font-size: 11px;
          color: var(--text-quaternary);
          text-transform: uppercase;
          letter-spacing: 0.09em;
        }

        .flow-head__text h3 {
          font-family: "Fraunces", serif;
          font-size: 24px;
          line-height: 1.16;
          font-weight: 500;
          margin: 0 0 6px;
        }

        .flow-close {
          border: none;
          background: rgba(255, 255, 255, 0.74);
          border-radius: 12px;
          width: 34px;
          height: 34px;
          font-size: 20px;
          color: var(--text-tertiary);
          cursor: pointer;
        }

        .flow-meta {
          margin-top: 14px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .flow-meta__step {
          font-size: 12px;
          color: var(--text-tertiary);
        }

        .flow-progress {
          flex: 1;
          height: 8px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.78);
          overflow: hidden;
        }

        .flow-progress span {
          display: block;
          height: 100%;
          width: 0;
          border-radius: 999px;
          background: linear-gradient(90deg, var(--coral-secondary), var(--coral-primary));
          transition: width 0.3s ease;
        }

        .flow-body {
          margin-top: 16px;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.72);
          border: 1px solid rgba(255, 255, 255, 0.82);
          padding: 16px 14px;
          min-height: 370px;
          display: flex;
          flex-direction: column;
        }

        .flow-question {
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.07em;
          color: var(--coral-primary);
          font-weight: 600;
        }

        .flow-prompt {
          margin-top: 6px;
          font-family: "Fraunces", serif;
          font-size: 26px;
          line-height: 1.2;
        }

        .flow-help {
          margin-top: 6px;
          font-size: 13px;
          color: var(--text-tertiary);
        }

        .flow-input {
          margin-top: 14px;
          width: 100%;
          border-radius: 14px;
          border: 1px solid rgba(255, 255, 255, 0.9);
          background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(255, 245, 240, 0.74));
          padding: 12px;
          font-family: inherit;
          font-size: 15px;
          color: var(--text-primary);
        }

        .flow-input:focus {
          outline: none;
          border-color: rgba(255, 107, 74, 0.42);
          box-shadow: 0 0 0 3px rgba(255, 107, 74, 0.11);
        }

        .option-grid {
          margin-top: 14px;
          display: grid;
          gap: 10px;
        }

        .option-btn {
          border: none;
          border-radius: 14px;
          padding: 11px 12px;
          font-size: 14px;
          text-align: left;
          color: var(--text-secondary);
          cursor: pointer;
          background: rgba(255, 255, 255, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.84);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.84);
          transition: all 0.2s ease;
        }

        .option-btn:hover {
          border-color: rgba(255, 138, 106, 0.4);
        }

        .option-btn.is-selected {
          background: linear-gradient(145deg, rgba(255, 138, 106, 0.2), rgba(255, 255, 255, 0.85));
          border-color: rgba(255, 107, 74, 0.45);
          color: var(--text-primary);
        }

        .flow-error {
          min-height: 20px;
          margin-top: 10px;
          font-size: 12px;
          color: #d24a2e;
        }

        .flow-actions {
          margin-top: auto;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          padding-top: 12px;
        }

        .flow-btn {
          border: none;
          border-radius: 14px;
          padding: 12px 14px;
          font-size: 14px;
          font-weight: 600;
          font-family: "DM Sans", sans-serif;
          cursor: pointer;
        }

        .flow-btn[disabled] {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .flow-btn--ghost {
          background: rgba(255, 255, 255, 0.8);
          color: var(--text-secondary);
          border: 1px solid rgba(255, 255, 255, 0.88);
        }

        .flow-btn--primary {
          background: linear-gradient(135deg, var(--coral-secondary), var(--coral-primary));
          color: #fff;
          box-shadow: 0 8px 22px rgba(255, 107, 74, 0.22);
        }

        .flow-skip {
          margin-top: 4px;
          font-size: 12px;
          border: none;
          background: transparent;
          color: var(--blue-primary);
          cursor: pointer;
          padding: 4px 2px;
          align-self: flex-start;
        }

        .fade-in {
          opacity: 0;
          transform: translateY(24px);
          transition: opacity 0.8s ease, transform 0.8s ease;
        }

        .fade-in.visible {
          opacity: 1;
          transform: translateY(0);
        }

        .fade-in-stagger > * {
          opacity: 0;
          transform: translateY(16px);
          transition: opacity 0.6s ease, transform 0.6s ease;
        }

        .fade-in-stagger.visible > *:nth-child(1) {
          opacity: 1;
          transform: translateY(0);
          transition-delay: 0.1s;
        }

        .fade-in-stagger.visible > *:nth-child(2) {
          opacity: 1;
          transform: translateY(0);
          transition-delay: 0.25s;
        }

        .fade-in-stagger.visible > *:nth-child(3) {
          opacity: 1;
          transform: translateY(0);
          transition-delay: 0.4s;
        }

        @keyframes orbFloat {
          0%,
          100% {
            transform: translate(0, 0) scale(1);
          }
          25% {
            transform: translate(30px, -20px) scale(1.05);
          }
          50% {
            transform: translate(-20px, 15px) scale(0.95);
          }
          75% {
            transform: translate(15px, 25px) scale(1.02);
          }
        }

        @keyframes fadeSlideUp {
          from {
            opacity: 0;
            transform: translateY(24px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes breathe {
          0%,
          100% {
            transform: scale(1);
            opacity: 0.3;
          }
          50% {
            transform: scale(1.4);
            opacity: 0.6;
          }
        }

        @keyframes dotPulse {
          0%,
          100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.06);
          }
        }

        @media (max-width: 900px) {
          .nav__links {
            display: none;
          }

          .hero {
            text-align: center;
          }

          .hero__stage {
            grid-template-columns: 1fr;
            gap: 30px;
          }

          .hero__content {
            max-width: unset;
          }

          .hero__actions {
            justify-content: center;
            flex-wrap: wrap;
          }

          .compare-duo {
            grid-template-columns: 1fr;
            max-width: 440px;
            margin-left: auto;
            margin-right: auto;
          }

          .action-body {
            grid-template-columns: 1fr;
            gap: 32px;
          }

          .action-aside {
            flex-direction: row;
            justify-content: center;
            flex-wrap: wrap;
          }

          .growth-row {
            grid-template-columns: 1fr;
            max-width: 400px;
            margin-left: auto;
            margin-right: auto;
          }

          .profile-flow {
            padding: 14px;
          }

          .flow-body {
            min-height: 350px;
          }

          .page {
            height: auto;
            min-height: 100vh;
            max-height: none;
          }
        }

        @media (max-width: 600px) {
          .container {
            padding: 0 20px;
          }

          .hero__actions {
            flex-direction: column;
            align-items: stretch;
          }

          .auth-shell {
            padding: 18px;
            border-radius: 20px;
          }

          .auth-title {
            font-size: 25px;
          }

          .flow-head__text h3 {
            font-size: 21px;
          }

          .flow-prompt {
            font-size: 23px;
          }

          .flow-body {
            min-height: 340px;
            padding: 14px 12px;
          }

          .flow-actions {
            grid-template-columns: 1fr;
          }

          .page {
            height: auto;
            min-height: 100vh;
            max-height: none;
          }
        }
      `}</style>
    </div>
  );
}
