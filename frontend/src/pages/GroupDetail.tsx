import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { expensesApi, groupsApi, settlementsApi } from "../api/client";
import { Button, Card, Input, Spinner } from "../components/ui";
import type {
  Expense,
  GroupBalances,
  GroupDetail,
  Member,
  Settlement,
} from "../types";

type SplitType = "equal" | "exact" | "percentage";

export function GroupDetailPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const gid = Number(groupId);
  const navigate = useNavigate();

  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [balances, setBalances] = useState<GroupBalances | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"expenses" | "balances" | "members">("expenses");
  const [showAddExpense, setShowAddExpense] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const [showSettle, setShowSettle] = useState(false);
  const [error, setError] = useState("");

  const loadAll = async () => {
    try {
      const [g, b, e, s] = await Promise.all([
        groupsApi.get(gid),
        groupsApi.balances(gid),
        expensesApi.list(gid),
        settlementsApi.list(gid),
      ]);
      setGroup(g);
      setBalances(b);
      setExpenses(e);
      setSettlements(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load group");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gid]);

  if (loading) return <Spinner />;
  if (!group) return <div className="p-8 text-center text-gray-500">Group not found.</div>;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <button
        onClick={() => navigate("/groups")}
        className="mb-4 text-sm text-gray-500 hover:text-gray-800"
      >
        ← Back to groups
      </button>
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{group.name}</h1>
        <p className="text-sm text-gray-500">{group.currency}</p>
      </header>

      {error && <p className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <div className="mb-6 flex gap-2 border-b border-gray-200">
        {(["expenses", "balances", "members"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium capitalize ${
              tab === t
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "expenses" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setShowAddExpense((s) => !s)}>
              {showAddExpense ? "Cancel" : "+ Add expense"}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setShowSettle((s) => !s)}>
              {showSettle ? "Cancel" : "Settle up"}
            </Button>
          </div>

          {showAddExpense && group && (
            <AddExpenseForm
              group={group}
              onDone={() => {
                setShowAddExpense(false);
                loadAll();
              }}
              onError={setError}
            />
          )}

          {showSettle && balances && group && (
            <SettleUpForm
              group={group}
              balances={balances}
              onDone={() => {
                setShowSettle(false);
                loadAll();
              }}
              onError={setError}
            />
          )}

          {settlements.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-gray-700">Recent settlements</h3>
              {settlements.map((s) => {
                const fromName = group.members.find((m) => m.user_id === s.from_user)?.name ?? "Someone";
                const toName = group.members.find((m) => m.user_id === s.to_user)?.name ?? "Someone";
                return (
                  <Card key={s.id} className="mb-2 p-3">
                    <p className="text-sm">
                      <span className="font-medium">{fromName}</span> paid{" "}
                      <span className="font-semibold text-green-700">
                        {group.currency} {s.amount}
                      </span>{" "}
                      to <span className="font-medium">{toName}</span>
                    </p>
                  </Card>
                );
              })}
            </div>
          )}

          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-700">Expenses</h3>
            {expenses.length === 0 && (
              <p className="text-sm text-gray-500">No expenses yet. Add one to get started.</p>
            )}
            {expenses.map((e) => (
              <ExpenseRow
                key={e.id}
                expense={e}
                members={group.members}
                currency={group.currency}
                onDelete={async () => {
                  await expensesApi.delete(gid, e.id);
                  await loadAll();
                }}
              />
            ))}
          </div>
        </div>
      )}

      {tab === "balances" && balances && (
        <BalancesView balances={balances} currency={group.currency} />
      )}

      {tab === "members" && (
        <MembersView
          group={group}
          onChanged={loadAll}
          onError={setError}
          showAdd={showAddMember}
          setShowAdd={setShowAddMember}
        />
      )}
    </div>
  );
}

function ExpenseRow({
  expense,
  members,
  currency,
  onDelete,
}: {
  expense: Expense;
  members: Member[];
  currency: string;
  onDelete: () => Promise<void>;
}) {
  const creator = members.find((m) => m.user_id === expense.created_by)?.name ?? "Someone";
  const payers = expense.participants
    .filter((p) => Number(p.paid_share) > 0)
    .map((p) => members.find((m) => m.user_id === p.user_id)?.name ?? "Someone")
    .join(", ");

  return (
    <Card className="mb-2 flex items-center justify-between p-4">
      <div>
        <p className="font-medium text-gray-900">{expense.description}</p>
        <p className="text-xs text-gray-500">
          Paid by {payers || creator} · split {expense.split_type}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-semibold text-gray-900">
          {currency} {expense.total_amount}
        </span>
        <Button variant="ghost" size="sm" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </Card>
  );
}

function AddExpenseForm({
  group,
  onDone,
  onError,
}: {
  group: GroupDetail;
  onDone: () => void;
  onError: (msg: string) => void;
}) {
  const [description, setDescription] = useState("");
  const [total, setTotal] = useState("");
  const [splitType, setSplitType] = useState<SplitType>("equal");
  // Per-member shares: { [userId]: { paid, owed } }
  const [shares, setShares] = useState<Record<number, { paid: string; owed: string }>>(
    Object.fromEntries(group.members.map((m) => [m.user_id, { paid: "", owed: "" }])),
  );
  const [submitting, setSubmitting] = useState(false);

  const totalNum = Number(total) || 0;
  const memberCount = group.members.length;

  // Auto-distribute owed shares for "equal"
  useEffect(() => {
    if (splitType === "equal" && totalNum > 0 && memberCount > 0) {
      const per = (totalNum / memberCount).toFixed(2);
      setShares((prev) => {
        const next = { ...prev };
        for (const m of group.members) {
          next[m.user_id] = { ...next[m.user_id], owed: per };
        }
        return next;
      });
    }
    if (splitType === "percentage" && memberCount > 0) {
      const per = (100 / memberCount).toFixed(2);
      setShares((prev) => {
        const next = { ...prev };
        for (const m of group.members) {
          next[m.user_id] = { ...next[m.user_id], owed: per };
        }
        return next;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [splitType, total, memberCount]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError("");
    setSubmitting(true);
    try {
      const participants = group.members.map((m) => {
        const s = shares[m.user_id] ?? { paid: "0", owed: "0" };
        let owed = s.owed || "0";
        if (splitType === "percentage") {
          owed = ((Number(owed) || 0) * totalNum / 100).toFixed(2);
        }
        return {
          user_id: m.user_id,
          paid_share: s.paid || "0",
          owed_share: owed,
        };
      });
      await expensesApi.create(group.id, {
        description,
        total_amount: total,
        split_type: splitType,
        participants,
      });
      onDone();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to add expense");
    } finally {
      setSubmitting(false);
    }
  };

  const paidSum = Object.values(shares).reduce((acc, s) => acc + (Number(s.paid) || 0), 0);
  const owedSum = Object.values(shares).reduce((acc, s) => {
    if (splitType === "percentage") return acc + (Number(s.owed) || 0) * totalNum / 100;
    return acc + (Number(s.owed) || 0);
  }, 0);

  return (
    <Card className="p-6">
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          placeholder="e.g. Dinner, Groceries..."
        />
        <Input
          label="Total amount"
          type="number"
          step="0.01"
          value={total}
          onChange={(e) => setTotal(e.target.value)}
          required
        />
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Split type</label>
          <select
            value={splitType}
            onChange={(e) => setSplitType(e.target.value as SplitType)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="equal">Equal</option>
            <option value="exact">Exact amounts</option>
            <option value="percentage">Percentages</option>
          </select>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Who paid & how much each owes</p>
          {group.members.map((m) => (
            <div key={m.user_id} className="flex items-center gap-2">
              <span className="w-32 truncate text-sm text-gray-700">{m.name}</span>
              <input
                type="number"
                step="0.01"
                placeholder="Paid"
                value={shares[m.user_id]?.paid ?? ""}
                onChange={(e) =>
                  setShares((prev) => ({
                    ...prev,
                    [m.user_id]: { ...prev[m.user_id], paid: e.target.value },
                  }))
                }
                className="w-28 rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
              />
              <input
                type="number"
                step="0.01"
                placeholder={splitType === "percentage" ? "Owed %" : "Owed"}
                value={shares[m.user_id]?.owed ?? ""}
                onChange={(e) =>
                  setShares((prev) => ({
                    ...prev,
                    [m.user_id]: { ...prev[m.user_id], owed: e.target.value },
                  }))
                }
                className="w-28 rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
              />
            </div>
          ))}
        </div>

        <div className="text-xs text-gray-500">
          Paid total: {paidSum.toFixed(2)} / {totalNum.toFixed(2)} ·
          Owed total: {owedSum.toFixed(2)} / {totalNum.toFixed(2)}
          {Math.abs(paidSum - totalNum) > 0.01 && (
            <span className="text-red-600"> · Paid sum must equal total</span>
          )}
          {Math.abs(owedSum - totalNum) > 0.01 && (
            <span className="text-red-600"> · Owed sum must equal total</span>
          )}
        </div>

        <Button type="submit" disabled={submitting}>
          {submitting ? "Adding..." : "Add expense"}
        </Button>
      </form>
    </Card>
  );
}

function SettleUpForm({
  group,
  balances,
  onDone,
  onError,
}: {
  group: GroupDetail;
  balances: GroupBalances;
  onDone: () => void;
  onError: (msg: string) => void;
}) {
  const [fromUserId, setFromUserId] = useState<number | "">("");
  const [toUserId, setToUserId] = useState<number | "">("");
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError("");
    setSubmitting(true);
    try {
      await settlementsApi.create(group.id, {
        from_user_id: Number(fromUserId),
        to_user_id: Number(toUserId),
        amount,
      });
      onDone();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to record settlement");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-6">
      <h3 className="mb-4 font-semibold text-gray-900">Record a payment</h3>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">From (payer)</label>
          <select
            value={fromUserId}
            onChange={(e) => setFromUserId(Number(e.target.value))}
            required
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select member...</option>
            {group.members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">To (payee)</label>
          <select
            value={toUserId}
            onChange={(e) => setToUserId(Number(e.target.value))}
            required
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select member...</option>
            {group.members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <Input
          label="Amount"
          type="number"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          required
        />
        {balances.simplified_debts.length > 0 && (
          <div className="rounded-lg bg-brand-50 p-3 text-xs text-brand-700">
            <p className="mb-1 font-semibold">Suggested settlements:</p>
            {balances.simplified_debts.map((d, i) => (
              <p key={i}>
                {d.from_name} → {d.to_name}: {group.currency} {d.amount}
              </p>
            ))}
          </div>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Recording..." : "Record payment"}
        </Button>
      </form>
    </Card>
  );
}

function BalancesView({ balances, currency }: { balances: GroupBalances; currency: string }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="mb-2 text-sm font-semibold text-gray-700">Member balances</h3>
        <div className="space-y-2">
          {balances.balances.map((b) => {
            const val = Number(b.balance);
            const color = val > 0.01 ? "text-green-700" : val < -0.01 ? "text-red-600" : "text-gray-500";
            const label = val > 0.01 ? "is owed" : val < -0.01 ? "owes" : "settled up";
            return (
              <Card key={b.user_id} className="flex items-center justify-between p-4">
                <span className="font-medium text-gray-900">{b.name}</span>
                <span className={`text-sm font-semibold ${color}`}>
                  {val > 0.01 ? "+" : ""}
                  {currency} {Math.abs(val).toFixed(2)} · {label}
                </span>
              </Card>
            );
          })}
        </div>
      </div>

      {balances.simplified_debts.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-700">Suggested settlements</h3>
          <div className="space-y-2">
            {balances.simplified_debts.map((d, i) => (
              <Card key={i} className="p-4">
                <p className="text-sm text-gray-700">
                  <span className="font-medium">{d.from_name}</span> should pay{" "}
                  <span className="font-medium">{d.to_name}</span>{" "}
                  <span className="font-semibold text-green-700">
                    {currency} {d.amount}
                  </span>
                </p>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MembersView({
  group,
  onChanged,
  onError,
  showAdd,
  setShowAdd,
}: {
  group: GroupDetail;
  onChanged: () => void;
  onError: (msg: string) => void;
  showAdd: boolean;
  setShowAdd: (s: boolean) => void;
}) {
  const [email, setEmail] = useState("");
  const [adding, setAdding] = useState(false);

  const onAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    onError("");
    setAdding(true);
    try {
      await groupsApi.addMember(group.id, email);
      setEmail("");
      setShowAdd(false);
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to add member");
    } finally {
      setAdding(false);
    }
  };

  const onRemove = async (userId: number) => {
    try {
      await groupsApi.removeMember(group.id, userId);
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  return (
    <div className="space-y-4">
      <Button size="sm" onClick={() => setShowAdd(!showAdd)}>
        {showAdd ? "Cancel" : "+ Add member"}
      </Button>
      {showAdd && (
        <Card className="p-6">
          <form onSubmit={onAdd} className="space-y-4">
            <Input
              label="Member email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="friend@example.com"
            />
            <Button type="submit" disabled={adding}>
              {adding ? "Adding..." : "Add member"}
            </Button>
          </form>
        </Card>
      )}
      <div className="space-y-2">
        {group.members.map((m) => (
          <Card key={m.user_id} className="flex items-center justify-between p-4">
            <div>
              <p className="font-medium text-gray-900">{m.name}</p>
              <p className="text-sm text-gray-500">{m.email}</p>
            </div>
            {m.user_id !== group.created_by && (
              <Button variant="ghost" size="sm" onClick={() => onRemove(m.user_id)}>
                Remove
              </Button>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
