// TypeScript types mirroring backend Pydantic schemas.
export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Member {
  user_id: number;
  name: string;
  email: string;
  joined_at: string;
}

export interface Group {
  id: number;
  name: string;
  currency: string;
  created_by: number;
  created_at: string;
}

export interface GroupDetail extends Group {
  members: Member[];
}

export interface Participant {
  user_id: number;
  paid_share: string;
  owed_share: string;
}

export interface Expense {
  id: number;
  group_id: number;
  description: string;
  total_amount: string;
  split_type: "equal" | "exact" | "percentage";
  created_by: number;
  created_at: string;
  participants: Participant[];
}

export interface UserBalance {
  user_id: number;
  name: string;
  balance: string; // positive = is owed money, negative = owes
}

export interface SimplifiedDebt {
  from_user_id: number;
  from_name: string;
  to_user_id: number;
  to_name: string;
  amount: string;
}

export interface GroupBalances {
  balances: UserBalance[];
  simplified_debts: SimplifiedDebt[];
}

export interface Settlement {
  id: number;
  group_id: number;
  from_user: number;
  to_user: number;
  amount: string;
  created_at: string;
}
