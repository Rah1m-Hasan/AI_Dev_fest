import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, BookOpen, Check, CircleHelp, PiggyBank, ShieldCheck, WalletCards } from 'lucide-react';
import { ErrorState, LoadingPage, PageHeader, Tag } from '../ui';
import { CategoryTabs } from '../ui/CategoryTabs';
import { learningAPI } from '../../api/client';
import type { LearningResponse, LessonCard, LessonDetail, LessonProgressSummary } from '../../types';
import { LessonDetailSheet } from './LessonDetailSheet';

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  'Money Basics': <WalletCards size={16} />,
  Budgeting: <WalletCards size={16} />,
  Saving: <PiggyBank size={16} />,
  'MFS Basics': <BookOpen size={16} />,
  'Digital Safety': <ShieldCheck size={16} />,
};

function LessonCardView({ lesson, featured = false, open }: { lesson: LessonCard; featured?: boolean; open: () => void }) {
  return <article className={`card lesson-card ${featured ? 'lesson-card--featured' : 'lesson-card--compact'}`} onClick={open}>
    <div className="lesson-card__header">
      <span className={`lesson-card__icon${featured ? '' : ' lesson-card__icon--sm'}`}>{CATEGORY_ICONS[lesson.category] || <BookOpen size={16} />}</span>
      <span className="lesson-card__category">{lesson.category}</span>
      <span className="lesson-card__duration">{lesson.duration_minutes} min</span>
    </div>
    <div className="lesson-card__copy">
      <h3>{lesson.title}</h3>
      <p className="lesson-card__summary">{lesson.summary}</p>
    </div>
    {lesson.trigger_reason && <p className="lesson-card__reason"><CircleHelp size={14} />{lesson.trigger_reason}</p>}
    <div className="lesson-card__footer">
      {lesson.completed ? <span className="lesson-card__complete"><Check size={14} />Completed</span> : <span />}
      <button className="text-button" onClick={(event) => { event.stopPropagation(); open(); }}>
        {lesson.completed ? 'Review lesson' : 'Start lesson'} <ArrowRight size={14} />
      </button>
    </div>
  </article>;
}

export function LearnExperience() {
  const navigate = useNavigate();
  const location = useLocation();
  const openedFromOffer = useRef<number | null>(null);
  const [data, setData] = useState<LearningResponse | null>(null);
  const [catalog, setCatalog] = useState<LessonCard[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('For You');
  const [selectedLesson, setSelectedLesson] = useState<LessonCard | null>(null);
  const [lessonDetail, setLessonDetail] = useState<LessonDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [completing, setCompleting] = useState<string | null>(null);

  const refreshRecommendations = async () => {
    const next = await learningAPI.recommendations();
    setData(next);
    return next;
  };

  useEffect(() => { void refreshRecommendations().catch(() => setError('Could not load your personalized lessons.')); }, []);

  useEffect(() => {
    if (activeTab === 'For You') return;
    let live = true;
    learningAPI.lessons(activeTab)
      .then((result: { lessons: LessonCard[] }) => { if (live) setCatalog(result.lessons); })
      .catch(() => { if (live) setError('Could not load this lesson category.'); });
    return () => { live = false; };
  }, [activeTab]);

  const completedCount = useMemo(() => data?.progress.reduce((sum, item) => sum + item.completed, 0) ?? 0, [data]);
  const recommendedCount = useMemo(() => data ? [data.featured, ...data.for_you].filter((item): item is LessonCard => item !== null).filter((item) => !item.completed).length : 0, [data]);

  const handleLessonClick = async (lesson: LessonCard) => {
    setSelectedLesson(lesson); setLessonDetail(null); setDetailLoading(true);
    try {
      const detail = await learningAPI.lessonDetail(lesson.id);
      setLessonDetail(detail);
      if (!detail.started) await learningAPI.startLesson(lesson.id);
    } catch { setLessonDetail(null); }
    finally { setDetailLoading(false); }
  };

  const handleComplete = async (lessonId: number, quizAnswer?: string) => {
    setCompleting(String(lessonId));
    try {
      await learningAPI.completeLesson(lessonId, quizAnswer);
      setSelectedLesson(null); setLessonDetail(null);
      await refreshRecommendations();
      if (activeTab !== 'For You') {
        const result = await learningAPI.lessons(activeTab) as { lessons: LessonCard[] };
        setCatalog(result.lessons);
      }
    } finally { setCompleting(null); }
  };

  useEffect(() => {
    const lessonId = Number(new URLSearchParams(location.search).get('lesson'));
    if (!lessonId || openedFromOffer.current === lessonId || !data) return;
    openedFromOffer.current = lessonId;
    let live = true;
    setDetailLoading(true);
    learningAPI.lessonDetail(lessonId).then(async (detail) => {
      if (!live) return;
      setSelectedLesson(detail); setLessonDetail(detail);
      if (!detail.started) await learningAPI.startLesson(lessonId);
    }).catch(() => { if (live) setError('Could not load this lesson.'); }).finally(() => { if (live) setDetailLoading(false); });
    return () => { live = false; };
  }, [data, location.search]);

  if (error) return <ErrorState message={error} retry={() => { setError(null); void refreshRecommendations().catch(() => setError('Could not load your personalized lessons.')); }} />;
  if (!data) return <LoadingPage label="Loading your recommended lessons…" />;

  const sectionLessons = activeTab === 'For You' ? data.for_you : catalog;
  const totalConcepts = data.progress.reduce((sum, item) => sum + item.total, 0);

  return <div className="page learn-page">
    <PageHeader title="Learn" description="Build better money habits from the activity you already make." />

    <section className="learn-progress" aria-label="Your learning progress">
      <div className="learn-progress__top"><div><span className="eyebrow">Money knowledge</span><h2>Your learning progress</h2></div><strong>{completedCount} concepts completed · {recommendedCount} recommended next</strong></div>
      <div className="learn-progress__bar"><div className="learn-progress__fill" style={{ width: `${Math.round((completedCount / Math.max(1, totalConcepts)) * 100)}%` }} /></div>
      <div className="learn-progress__cats">{data.progress.map((item: LessonProgressSummary) => <span key={item.category}><b>{item.category}</b>{item.completed}/{item.total}</span>)}</div>
    </section>

    <div className="learn-tabs"><CategoryTabs tabs={data.tabs} active={activeTab} onChange={setActiveTab} /></div>

    {activeTab === 'For You' && data.featured && <section className="learn-recommendation" aria-labelledby="recommended-lessons-title">
      <div className="learn-section-heading"><div><h2 id="recommended-lessons-title">Recommended for you</h2><p>Based on your recent spending</p></div><Tag tone="ai">Personalized</Tag></div>
      <LessonCardView lesson={data.featured} featured open={() => void handleLessonClick(data.featured!)} />
    </section>}

    <section className="learn-library" aria-labelledby="lesson-library-title">
      <div className="learn-section-heading"><div><h2 id="lesson-library-title">{activeTab === 'For You' ? 'Keep learning' : activeTab}</h2><p>{activeTab === 'For You' ? 'Short next steps for your money habits' : 'Practical concepts you can finish in a few minutes'}</p></div></div>
      {sectionLessons.length ? <div className="lesson-grid">{sectionLessons.map((lesson) => <LessonCardView key={lesson.id} lesson={lesson} open={() => void handleLessonClick(lesson)} />)}</div> : <div className="state-card state-card--empty"><BookOpen /><h2>{activeTab === 'For You' ? "You're all caught up" : 'No lessons in this category yet'}</h2><p>{activeTab === 'For You' ? 'Explore more money topics or check back as your financial activity changes.' : 'Try another topic to keep building practical money knowledge.'}</p></div>}
    </section>

    {selectedLesson && <LessonDetailSheet
      lesson={lessonDetail} loading={detailLoading} completing={completing ? String(selectedLesson.id) : null}
      onClose={() => { setSelectedLesson(null); setLessonDetail(null); }}
      onComplete={(quizAnswer) => void handleComplete(selectedLesson.id, quizAnswer)}
      onAskAI={() => {
        const context = { type: 'learning_lesson', lessonId: selectedLesson.id, title: selectedLesson.title, concept: selectedLesson.category };
        navigate(`/coach/assistant?prompt=${encodeURIComponent(`Help me understand "${selectedLesson.title}". Keep this about ${selectedLesson.category} and use simple examples.`)}`, { state: { learningLesson: context } });
      }}
    />}
  </div>;
}
