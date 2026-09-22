import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { groupsApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Button, Card, Input, Spinner } from "../components/ui";
import type { Group } from "../types";

export function GroupsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    try {
      const data = await groupsApi.list();
      setGroups(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load groups");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setCreating(true);
    try {
      await groupsApi.create({ name, currency });
      setName("");
      setShowCreate(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create group");
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Your Groups</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{user?.name}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      </header>

      {error && <p className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      {groups.length === 0 && !showCreate && (
        <Card className="p-8 text-center">
          <p className="text-gray-500">You have no groups yet.</p>
          <Button className="mt-4" onClick={() => setShowCreate(true)}>
            Create your first group
          </Button>
        </Card>
      )}

      {groups.length > 0 && (
        <div className="mb-4">
          <Button size="sm" onClick={() => setShowCreate((s) => !s)}>
            {showCreate ? "Cancel" : "+ New group"}
          </Button>
        </div>
      )}

      {showCreate && (
        <Card className="mb-6 p-6">
          <form onSubmit={onCreate} className="space-y-4">
            <Input
              label="Group name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g. Weekend trip, Apartment..."
            />
            <Input
              label="Currency code"
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              maxLength={3}
              required
            />
            <div className="flex gap-2">
              <Button type="submit" disabled={creating}>
                {creating ? "Creating..." : "Create group"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {groups.map((g) => (
          <Card
            key={g.id}
            className="cursor-pointer p-5 transition-shadow hover:shadow-md"
          >
            <button onClick={() => navigate(`/groups/${g.id}`)} className="block w-full text-left">
              <h3 className="font-semibold text-gray-900">{g.name}</h3>
              <p className="mt-1 text-sm text-gray-500">{g.currency}</p>
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}
