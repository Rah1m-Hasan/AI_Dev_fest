import { useState } from 'react';
import { X, Check, BrainCircuit } from 'lucide-react';
import { Sheet, Tag } from '../ui';
import type { LessonDetail } from '../../types';

interface Props {
  lesson: LessonDetail | null;
  loading: boolean;
  completing: string | null;
  onClose: () => void;
  onComplete: (quizAnswer?: string) => void;
  onAskAI: () => void;
}

export function LessonDetailSheet({ lesson, loading, completing, onClose, onComplete, onAskAI }: Props) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [answered, setAnswered] = useState(false);
  const [showBangla, setShowBangla] = useState(false);

  const handleQuizSubmit = () => {
    if (!lesson?.quiz || answered) return;
    setAnswered(true);
  };

  const handleComplete = () => {
    const answer = lesson?.quiz ? selectedOption ?? undefined : undefined;
    onComplete(answer);
  };

  // Reset state when lesson changes
  const lessonId = lesson?.id;
  const [prevId, setPrevId] = useState<number | null>(null);
  if (lessonId !== prevId) {
    setPrevId(lessonId ?? null);
    setSelectedOption(null);
    setAnswered(false);
    setShowBangla(lesson?.initial_language === 'bn');
  }

  const isCorrect = lesson?.quiz && answered
    ? selectedOption === lesson.quiz.correct_key
    : null;

  const content = lesson?.content_bn && showBangla ? lesson.content_bn : lesson?.content;
  const persSection = lesson?.personalized_section_bn && showBangla
    ? lesson.personalized_section_bn
    : lesson?.personalized_section;

  return (
    <Sheet
      title={lesson?.title ?? 'Lesson'}
      close={onClose}
      className="lesson-detail-sheet"
    >
      {loading && (
        <div className="lesson-detail__loading">
          <div className="skeleton" style={{ height: 20, marginBottom: 12 }} />
          <div className="skeleton" style={{ height: 14, marginBottom: 8 }} />
          <div className="skeleton" style={{ height: 14, marginBottom: 8 }} />
          <div className="skeleton" style={{ height: 14, width: '70%' }} />
        </div>
      )}

      {!loading && lesson && (
        <div className="lesson-detail">
          {/* Meta */}
          <div className="lesson-detail__meta">
            <Tag tone="ai">{lesson.duration_minutes} min read</Tag>
            <Tag tone="neutral">{lesson.category}</Tag>
            {lesson.content_bn && (
              <button
                className="text-button text-button--sm"
                onClick={() => setShowBangla(!showBangla)}
              >
                {showBangla ? 'Read in English' : 'বাংলায় পড়ুন'}
              </button>
            )}
          </div>

          {/* Content */}
          <div className="lesson-detail__content">
            <h3>What this means</h3>
            {content?.split('\n\n').map((para, i) => <p key={i}>{para}</p>)}
          </div>

          {/* Personalized section */}
          {persSection && (
            <div className="lesson-detail__personalized">
              <h3>In your case</h3>
              <p>{persSection}</p>
            </div>
          )}

          {/* Practical takeaway */}
          <div className="lesson-detail__takeaway">
            <h3>Try it</h3>
            <p>
              {lesson.category === 'Budgeting' && 'If your monthly grocery target is ৳8,000, a simple weekly target is about ৳2,000. Check it each Friday.'}
              {lesson.category === 'Saving' && 'Set a small weekly savings target — even ৳100 a week builds momentum over time.'}
              {lesson.category === 'MFS Basics' && 'Use merchant payments instead of cash-out when possible to avoid withdrawal fees.'}
              {lesson.category === 'Digital Safety' && 'Review your PIN settings and never share your PIN with anyone, including family members.'}
              {!['Budgeting', 'Saving', 'MFS Basics', 'Digital Safety'].includes(lesson.category) && 'Apply what you learned to your next spending decision.'}
            </p>
          </div>

          {/* Quiz */}
          {lesson.quiz && (
            <div className="lesson-detail__quiz">
              <h3>Quick check</h3>
              <p className="lesson-detail__quiz-q">{lesson.quiz.question}</p>
              <div className="lesson-detail__quiz-options">
                {lesson.quiz.options.map((opt) => (
                  <button
                    key={opt.key}
                    className={`quiz-option${selectedOption === opt.key ? ' quiz-option--selected' : ''}${answered && opt.key === lesson.quiz!.correct_key ? ' quiz-option--correct' : ''}${answered && selectedOption === opt.key && opt.key !== lesson.quiz!.correct_key ? ' quiz-option--wrong' : ''}`}
                    onClick={() => !answered && setSelectedOption(opt.key)}
                    disabled={answered}
                  >
                    <span className="quiz-option__key">{opt.key}</span>
                    <span>{opt.text}</span>
                  </button>
                ))}
              </div>
              {answered && (
                <div className={`lesson-detail__quiz-feedback${isCorrect ? ' lesson-detail__quiz-feedback--correct' : ' lesson-detail__quiz-feedback--wrong'}`}>
                  {isCorrect ? (
                    <><Check size={16} /> Correct!</>
                  ) : (
                    <><X size={16} /> The right answer is {lesson.quiz.correct_key}: {lesson.quiz.options.find(o => o.key === lesson.quiz!.correct_key)?.text}</>
                  )}
                </div>
              )}
              {!answered && lesson.quiz && (
                <button
                  className="button button--secondary"
                  onClick={handleQuizSubmit}
                  disabled={!selectedOption}
                >
                  Check answer
                </button>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="lesson-detail__actions">
            <button
              className="button"
              onClick={handleComplete}
              disabled={completing !== null || Boolean(lesson.quiz && !answered && !lesson.completed)}
            >
              {completing ? 'Saving…' : lesson.completed ? <><Check size={15} /> Completed</> : <><Check size={15} /> Mark complete</>}
            </button>
            <button className="button button--ghost" onClick={onAskAI}>
              <BrainCircuit size={15} /> Ask AI about this
            </button>
          </div>

          <p className="lesson-detail__disclaimer">
            Financial concepts only — this does not constitute financial advice.
          </p>
        </div>
      )}
    </Sheet>
  );
}
