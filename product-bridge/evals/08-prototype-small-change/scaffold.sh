#!/usr/bin/env bash
# A minimal Next.js app (no node_modules) with an existing FieldError component to reuse,
# checked out on a prototype branch.
set -euo pipefail
mkdir -p app/rules/new components/ui
cat > package.json <<'EOF'
{
  "name": "rules-app",
  "private": true,
  "scripts": {"dev": "next dev", "lint": "next lint", "typecheck": "tsc --noEmit", "test": "vitest run"},
  "dependencies": {"next": "14.2.3", "react": "18.3.1", "react-dom": "18.3.1"},
  "devDependencies": {"typescript": "5.4.5", "vitest": "1.6.0", "@types/react": "18.3.3"}
}
EOF
cat > tsconfig.json <<'EOF'
{"compilerOptions": {"strict": true, "jsx": "preserve", "module": "esnext", "moduleResolution": "bundler", "baseUrl": ".", "paths": {"@/*": ["./*"]}}}
EOF
cat > app/rules/new/page.tsx <<'EOF'
import { RuleForm } from "@/components/RuleForm";

export default function NewRulePage() {
  return <RuleForm />;
}
EOF
cat > components/ui/Input.tsx <<'EOF'
import type { InputHTMLAttributes } from "react";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="input" {...props} />;
}
EOF
cat > components/ui/Button.tsx <<'EOF'
import type { ButtonHTMLAttributes } from "react";

export function Button(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className="btn btn-primary" {...props} />;
}
EOF
cat > components/ui/FieldError.tsx <<'EOF'
// Inline message under a field. Pair with aria-describedby on the input.
export function FieldError({ id, children }: { id: string; children: React.ReactNode }) {
  return <p id={id} role="alert" className="field-error">{children}</p>;
}
EOF
cat > components/RuleForm.tsx <<'EOF'
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function RuleForm() {
  const [name, setName] = useState("");
  const [threshold, setThreshold] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    await fetch("/api/rules", { method: "POST", body: JSON.stringify({ name, threshold: Number(threshold) }) });
  }

  return (
    <form onSubmit={onSubmit}>
      <label htmlFor="name">Name</label>
      <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
      <label htmlFor="threshold">Threshold</label>
      <Input id="threshold" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
      <Button type="submit">Save rule</Button>
    </form>
  );
}
EOF
printf 'node_modules/\n.next/\n' > .gitignore
git init -q -b main
git -c user.name=fixture -c user.email=fixture@example.com add -A
git -c user.name=fixture -c user.email=fixture@example.com commit -qm "rules app"
# The eval sandbox blocks writes under .git, so the branch is created here.
git checkout -qb pb/PB-001-threshold-error
