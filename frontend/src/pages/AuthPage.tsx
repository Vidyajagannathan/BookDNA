import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api } from "../lib/api";
export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next");
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    remember: true,
  });
  const mutation = useMutation({
    mutationFn: () =>
      mode === "login"
        ? api.login(form.email || form.username, form.password, form.remember)
        : api.register(form.username, form.email, form.password, form.remember),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: ["dna"] });
      nav(next?.startsWith("/") ? next : "/discover");
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };
  return (
    <section className="auth-page">
      <div className="auth-intro">
        <span className="eyebrow">Every reader has a pattern</span>
        <h1>
          {mode === "login"
            ? "Welcome back."
            : "Begin your literary fingerprint."}
        </h1>
        <p>
          No personality quiz. No genre boxes. Just your books, teaching BookDNA
          what makes you you.
        </p>
      </div>
      <form onSubmit={submit} className="auth-card">
        <h2>{mode === "login" ? "Sign in" : "Create your account"}</h2>
        {mode === "register" && (
          <label>
            Username
            <input
              required
              minLength={3}
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              autoComplete="username"
            />
          </label>
        )}
        <label>
          {mode === "login" ? "Email or username" : "Email"}
          <input
            required
            type={mode === "register" ? "email" : "text"}
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            required
            minLength={8}
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
          />
        </label>
        <label className="stay-signed-in">
          <input
            type="checkbox"
            checked={form.remember}
            onChange={(e) => setForm({ ...form, remember: e.target.checked })}
          />
          <span>
            Stay signed in for 30 days
            <small>You can sign out anytime from your account.</small>
          </span>
        </label>
        {mutation.error && <p className="error">{mutation.error.message}</p>}
        <button className="button primary" disabled={mutation.isPending}>
          {mutation.isPending
            ? "One moment…"
            : mode === "login"
              ? "Sign in"
              : "Create my BookDNA"}{" "}
          <ArrowRight size={17} />
        </button>
        <p>
          {mode === "login" ? (
            <>
              New here? <Link to="/register">Create an account</Link>
            </>
          ) : (
            <>
              By registering you agree to our <Link to="/terms">Terms</Link> and
              acknowledge our <Link to="/privacy">Privacy Policy</Link>.<br />
              Already have an account? <Link to="/login">Sign in</Link>
            </>
          )}
        </p>
      </form>
    </section>
  );
}
