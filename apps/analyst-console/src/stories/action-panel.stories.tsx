import type { Meta, StoryObj } from "@storybook/react";

import { ActionPanel } from "@/features/actions/action-panel";

const meta: Meta<typeof ActionPanel> = {
  title: "Analyst Console/ActionPanel",
  component: ActionPanel,
};

export default meta;

type Story = StoryObj<typeof ActionPanel>;

export const Default: Story = {
  args: {
    authenticated: true,
    busy: false,
    item: {
      event_id: "evt-1",
      headline: "Alpha review item",
      country: "Colombia",
      review_priority: "high",
      event_type: "reform",
      salience: "high",
      confidence: "medium",
      review_status: "auto",
      summary: "Alpha summary keeps the review decision surface anchored.",
    },
    onSave: async () => {},
    saveError: null,
  },
};
