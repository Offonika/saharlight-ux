export interface SegmentedItem {
  value: string;
  icon?: React.ReactNode;
  label?: string;
}

interface SegmentedControlProps {
  value: string;
  onChange: (value: string) => void;
  items: SegmentedItem[];
}

export const SegmentedControl = ({ value, onChange, items }: SegmentedControlProps) => {
  return (
    <div className="segmented">
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          className="segmented__item"
          aria-pressed={value === item.value}
          onClick={() => onChange(item.value)}
        >
          {item.icon && <span className="segmented__icon">{item.icon}</span>}
          {item.label && <span className="segmented__label">{item.label}</span>}
        </button>
      ))}
    </div>
  );
};
