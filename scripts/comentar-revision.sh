#!/usr/bin/env bash
# Publica o actualiza el comentario de la revisión automática de una PR (HU-36).
# Lo usa .github/workflows/revision-automatica.yml. Necesita GH_TOKEN, GITHUB_REPOSITORY,
# PR, SHA, MODEL y AGENT_STATUS (código de salida del agente); lee la revisión de review.md.
set -euo pipefail

MARKER='<!-- revision-automatica -->'
MAX_LINES=500

if [ "${AGENT_STATUS:-1}" = "0" ] && [ -s review.md ]; then
  sed -r 's/\x1b\[[0-9;]*[A-Za-z]//g' review.md > review-clean.md
  body=$(sed -n "1,${MAX_LINES}p" review-clean.md)
  if [ "$(wc -l < review-clean.md)" -gt "$MAX_LINES" ]; then
    body="${body}

_Revisión recortada a ${MAX_LINES} líneas._"
  fi
elif [ "${AGENT_STATUS:-1}" = "124" ]; then
  body="No se ha podido hacer la revisión automática de este commit: el modelo no ha respondido en 10 minutos. La revisión de una persona sigue siendo necesaria, como siempre."
else
  body="No se ha podido hacer la revisión automática de este commit (código ${AGENT_STATUS:-desconocido}; el final del log está en el paso \"Revisión con el agente\"). La revisión de una persona sigue siendo necesaria, como siempre."
fi

{
  echo "$MARKER"
  echo "### Revisión automática · OpenCode (${MODEL})"
  echo
  echo "Commit revisado: \`${SHA:0:7}\`. Es una ayuda para quien revisa: no sustituye a la revisión de una persona ni bloquea la PR. Se actualiza en cada push."
  echo
  echo "$body"
} > comment.md

comment_id=$(gh api "repos/${GITHUB_REPOSITORY}/issues/${PR}/comments" --paginate \
  --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"${MARKER}\"))) | .id" \
  | sed -n '1p')

if [ -n "$comment_id" ]; then
  gh api --method PATCH "repos/${GITHUB_REPOSITORY}/issues/comments/${comment_id}" -F body=@comment.md > /dev/null
  echo "Comentario ${comment_id} actualizado"
else
  gh pr comment "$PR" --repo "$GITHUB_REPOSITORY" --body-file comment.md
fi
