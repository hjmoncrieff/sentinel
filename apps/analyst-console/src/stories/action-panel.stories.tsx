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
    item: {
      event_id: "evt-1",
      headline: "Alpha review item",
      country: "Colombia",
      review_priority: "high",
      publication_status: "withheld",
      council_disagreement_summary: "aligned",
      supervision_reasons: [
        "qa_flags",
        "high_salience_unreviewed",
      ],
      council_recommended_actions: [
        {
          code: "human_corroboration",
          priority: "high",
          reason:
            "Low-confidence event should be corroborated before publication.",
        },
      ],
    },
  },
};
