import React from "react";
import InputMask from "react-input-mask";

interface TimeInputProps {
  value: string;
  onChange: (val: string) => void;
  className?: string;
}

const TimeInput: React.FC<TimeInputProps> = ({ value, onChange, className }) => {
  const isTelegram = React.useMemo(() => {
    return typeof window !== "undefined" && Boolean(window.Telegram?.WebApp);
  }, []);

  const isIOS = React.useMemo(() => {
    return (
      typeof navigator !== "undefined" &&
      /iPad|iPhone|iPod/.test(navigator.userAgent)
    );
  }, []);

  if (isTelegram || isIOS) {
    return (
      <InputMask
        mask="99:99"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {(inputProps) => (
          <input
            {...inputProps}
            type="text"
            className={className}
            placeholder="HH:MM"
          />
        )}
      </InputMask>
    );
  }

  return (
    <input
      type="time"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    />
  );
};

export default TimeInput;
