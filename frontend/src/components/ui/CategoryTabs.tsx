import { Check } from 'lucide-react';

interface CategoryTabsProps {
  tabs: string[];
  active: string;
  onChange: (tab: string) => void;
}

export function CategoryTabs({ tabs, active, onChange }: CategoryTabsProps) {
  return (
    <div className="category-tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab}
          role="tab"
          aria-selected={active === tab}
          className={`category-tab${active === tab ? ' category-tab--active' : ''}`}
          onClick={() => onChange(tab)}
        >
          {active === tab && <Check size={13} />}
          {tab}
        </button>
      ))}
    </div>
  );
}
