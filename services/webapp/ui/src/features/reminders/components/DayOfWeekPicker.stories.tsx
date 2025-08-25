import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import DayOfWeekPicker from "./DayOfWeekPicker";

const meta: Meta<typeof DayOfWeekPicker> = {
  title: "Reminders/DayOfWeekPicker",
  component: DayOfWeekPicker,
};

export default meta;

export const Basic: StoryObj<typeof DayOfWeekPicker> = {
  render: () => {
    const [value, setValue] = useState<number[]>([]);
    const short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
    const long = [
      "Понедельник",
      "Вторник",
      "Среда",
      "Четверг",
      "Пятница",
      "Суббота",
      "Воскресенье",
    ];
    return (
      <DayOfWeekPicker
        value={value}
        onChange={setValue}
        shortNames={short}
        longNames={long}
      />
    );
  },
};
