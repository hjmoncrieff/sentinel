import type { ConsoleState, QueueItem } from "@/lib/domain/types";

export const initialConsoleState: ConsoleState = {
  queue: [],
  selectedId: null,
  search: "",
  priorityFilter: "all",
  queueScope: "all",
  worklistFilter: "all",
  countryFilter: "all",
  categoryFilter: "all",
  sortOrder: "priority",
  workspace: "review",
  middleTab: "briefing",
  loadError: null,
};

export type ConsoleAction =
  | { type: "queueLoaded"; payload: QueueItem[] }
  | { type: "loadFailed"; payload: string }
  | { type: "selected"; payload: string }
  | { type: "searchChanged"; payload: string }
  | { type: "priorityChanged"; payload: ConsoleState["priorityFilter"] }
  | { type: "queueScopeChanged"; payload: ConsoleState["queueScope"] }
  | { type: "worklistFilterChanged"; payload: ConsoleState["worklistFilter"] }
  | { type: "countryFilterChanged"; payload: ConsoleState["countryFilter"] }
  | { type: "categoryFilterChanged"; payload: ConsoleState["categoryFilter"] }
  | { type: "sortOrderChanged"; payload: ConsoleState["sortOrder"] }
  | { type: "workspaceChanged"; payload: ConsoleState["workspace"] }
  | { type: "middleTabChanged"; payload: ConsoleState["middleTab"] }
  | { type: "queueItemInserted"; payload: QueueItem }
  | { type: "queueItemPatched"; payload: { eventId: string; patch: Partial<QueueItem> } };

export function consoleReducer(
  state: ConsoleState,
  action: ConsoleAction,
): ConsoleState {
  switch (action.type) {
    case "queueLoaded":
      return {
        ...state,
        queue: action.payload,
        selectedId:
          action.payload.some((row) => row.event_id === state.selectedId)
            ? state.selectedId
            : action.payload[0]?.event_id ?? null,
        loadError: null,
      };
    case "loadFailed":
      return {
        ...state,
        loadError: action.payload,
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
    case "queueScopeChanged":
      return {
        ...state,
        queueScope: action.payload,
      };
    case "worklistFilterChanged":
      return {
        ...state,
        worklistFilter: action.payload,
      };
    case "countryFilterChanged":
      return {
        ...state,
        countryFilter: action.payload,
      };
    case "categoryFilterChanged":
      return {
        ...state,
        categoryFilter: action.payload,
      };
    case "sortOrderChanged":
      return {
        ...state,
        sortOrder: action.payload,
      };
    case "workspaceChanged":
      return {
        ...state,
        workspace: action.payload,
      };
    case "middleTabChanged":
      return {
        ...state,
        middleTab: action.payload,
      };
    case "queueItemInserted":
      return {
        ...state,
        queue: [action.payload, ...state.queue],
        selectedId: action.payload.event_id,
      };
    case "queueItemPatched":
      return {
        ...state,
        queue: state.queue.map((item) =>
          item.event_id === action.payload.eventId
            ? { ...item, ...action.payload.patch }
            : item,
        ),
      };
    default:
      return state;
  }
}
