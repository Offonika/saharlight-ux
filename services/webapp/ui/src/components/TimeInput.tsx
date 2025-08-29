import React from "react";
import InputMask from "react-input-mask";

interface TimeInputProps {
  value: string;
  onChange: (val: string) => void;
  className?: string;
}

const isIOS =
  /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  window.Telegram?.WebApp?.platform === "ios";

const TimeInput: React.FC<TimeInputProps> = ({ value, onChange, className }) => {
  if (isIOS) {
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
