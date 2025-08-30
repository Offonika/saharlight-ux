import React from "react";
import InputMask from "react-input-mask";

interface TimeInputProps {
  value: string;
  onChange: (val: string) => void;
  className?: string;
}

const TimeInput: React.FC<TimeInputProps> = ({ value, onChange, className }) => {
  const platform =
    typeof window !== "undefined" ? window.Telegram?.WebApp?.platform : undefined;
  const userAgent =
    typeof navigator !== "undefined" ? navigator.userAgent : undefined;

  const isIOS = React.useMemo(() => {
    if (!userAgent && !platform) {
      return false;
    }

    return /iPad|iPhone|iPod/.test(userAgent ?? "") || platform === "ios";
  }, [platform, userAgent]);

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
