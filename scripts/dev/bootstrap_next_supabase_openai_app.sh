#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/dev/bootstrap_next_supabase_openai_app.sh <app-name>"
  exit 1
fi

APP_NAME="$1"

pnpm create next-app@latest "$APP_NAME" \
  --ts \
  --eslint \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-pnpm \
  --yes

cd "$APP_NAME"

cat > .mise.toml <<'EOF'
[tools]
node = "22"
EOF

cat > .env.example <<'EOF'
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SERVICE_ROLE_KEY=
OPENAI_API_KEY=
EOF

pnpm add @supabase/supabase-js @supabase/ssr openai zod @tanstack/react-query react-hook-form
pnpm add -D playwright

echo
echo "Bootstrap complete for $APP_NAME"
echo
echo "Installed packages:"
echo "- Next.js: app framework for frontend and server routes"
echo "- Supabase SDKs: database, auth, storage, and SSR integration"
echo "- OpenAI SDK: model/API integration"
echo "- Zod: schema and env validation"
echo "- TanStack Query: client-side server state management"
echo "- React Hook Form: form handling"
echo "- Playwright: browser automation and end-to-end testing"
echo
echo "Next steps:"
echo "  cd $APP_NAME"
echo "  pnpm exec playwright install chromium"
echo "  cp .env.example .env.local"
