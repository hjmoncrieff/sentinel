import type { ConsoleState, QueueItem } from "@/lib/domain/types";

export const initialConsoleState: ConsoleState = {
  queue: [],
  selectedId: null,
  search: "",
  priorityFilter: "all",
  middleTab: "briefing",
  rightTab: "action",
};

export type ConsoleAction =
  | { type: "queueLoaded"; payload: QueueItem[] }
  | { type: "selected"; payload: string }
  | { type: "searchChanged"; payload: string }
  | { type: "priorityChanged"; payload: ConsoleState["priorityFilter"] };

export function consoleReducer(
  state: ConsoleState,
  action: ConsoleAction,
): ConsoleState {
  switch (action.type) {
    case "queueLoaded":
      return {
        ...state,
        queue: action.payload,
        selectedId: state.selectedId ?? action.payload[0]?.event_id ?? null,
      };
    case "selected":
      return {
        ...state,
        selectedId: action.payload,
      };
    case "searchChanged":
      return {
        ...state,
        search: action.payload,
      };
    case "priorityChanged":
      return {
        ...state,
        priorityFilter: action.payload,
      };
    default:
      return state;
  }
}
