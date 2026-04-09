export interface Task {
  id: string;
  hotel: string;
  checkin: string;
  checkout: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
}

export interface StepLog {
  id: number;
  task_id: string;
  platform: string;
  step_num: number;
  goal: string;
  screenshot_url: string;
  thinking: string | null;
  evaluation: string | null;
  memory: string | null;
  actions: ActionData[] | null;
  plan: PlanItem[] | null;
  url: string | null;
  created_at: string;
  engine?: 'browser-use' | 'page-agent' | null;
}

export interface ActionData {
  [key: string]: unknown;
}

export interface PlanItem {
  [key: string]: unknown;
}

export interface Result {
  id: number;
  task_id: string;
  platform: string;
  hotel_name: string | null;
  lowest_price: number | null;
  room_type: string | null;
  page_url: string | null;
  error: string | null;
  engine?: 'browser-use' | 'page-agent' | null;
  duration_seconds: number | null;
  strategy_name: string | null;
  attempt_number: number | null;
}
