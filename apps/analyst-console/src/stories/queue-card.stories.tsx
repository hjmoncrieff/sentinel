import type { Meta, StoryObj } from "@storybook/react";

import { QueueCard } from "@/features/queue/queue-card";

const meta: Meta<typeof QueueCard> = {
  title: "Analyst Console/QueueCard",
  component: QueueCard,
};

export default meta;

type Story = StoryObj<typeof QueueCard>;

export const Active: Story = {
  args: {
    active: true,
    onSelect: () => {},
    item: {
      event_id: "evt-1",
      headline: "Alpha review item",
      country: "Colombia",
      event_date: "2026-06-01",
      event_type: "reform",
      review_priority: "high",
    },
  },
};

export const Inactive: Story = {
  args: {
    active: false,
    onSelect: () => {},
    item: {
      event_id: "evt-2",
      headline: "Beta review item",
      country: "Mexico",
      event_date: "2026-06-02",
      event_type: "aid",
      review_priority: "low",
    },
  },
};
