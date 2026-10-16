# agent-schema · HU-25

> Equipo: [líder](lead.md) · Depende de: la spec · Bloquea a: [`agent-service`](agent-service.md)

## Tarea
Añadir los schemas de entrada de la HU-25, tal como define la sección "Schemas" de
`specs/HU-25-cambio-password-perfil.md`.

## Archivos
Solo `app/schemas/schema_user.py`. Los schemas existentes no se cambian.

## Lecturas
`AGENTS.md` → `specs/ontology.md` → la spec de HU-25 → `app/schemas/schema_user.py`.

## Contrato
- `UserProfileUpdate` (`extra="forbid"`):
  - `name: str | None`, `min_length=1`, `max_length=100`; `null` explícito → 422.
  - `email: EmailStr | None`; `null` explícito → 422.
  - `phone: str | None`, `max_length=20`; `null` lo borra.
  - Cualquier otro campo (`role`, `is_active`, `password`…) → 422.
  - Sin campos enviados, `model_dump(exclude_unset=True) == {}`.
- `PasswordChange` (`extra="forbid"`):
  - `current_password: str`, `min_length=1`.
  - `new_password: str`, `min_length=MIN_PASSWORD_LENGTH` (R-02).
- Ejemplos para Swagger en `json_schema_extra` y docstrings breves en español.

## Reglas
Sin comentarios `#`. Identificadores en inglés. No hace commit ni push. No toca
`docs/ai-log.md`.

## Verificación
- `ruff check app/schemas/schema_user.py`.
- Comprobación en Python: campos extra, `name=None`, `{}`, `phone=None` y `new_password`
  de 7 caracteres.

## Resultado
Entregado y aceptado sin cambios. Usa un `field_validator` (`reject_null`) para rechazar
`null` en `name` y `email` sin afectar al valor por defecto.
Aviso para el servicio: `EmailStr` solo pasa a minúsculas el dominio, así que
`normalize_email` sigue siendo necesario para R-01.
