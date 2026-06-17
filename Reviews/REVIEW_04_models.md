# Review 04 — Models (str + enrollment fixes)

**Status:** Code changes correct. **Database NOT yet migrated** — `models.py` and schema are out of sync.

## 🟢 Fixed (verified)
- `Instructor.__str__` / `Student.__str__` → `self.user.email` (string). Runtime test: no more TypeError.
- `Enrollment` FKs → `CASCADE` + non-null. Unique constraint now airtight (no NULL hole).
- **`Student.course` M2M removed** → M2M-vs-through contradiction (open since Review 01) is resolved. Relationship is now modeled exactly once, via `Enrollment`.

## 🔴 Action required
- Unmade migration `0002` pending: `Remove field course from student`, `Alter field course/student on enrollment`, etc.
- Run: `python manage.py makemigrations && python manage.py migrate`
- The earlier runtime test passed only because it hit the **old schema**. Re-run the shell chain *after* migrating to confirm against the real schema.
- **Concept:** `__str__` changes need no migration (Python only); FK/field changes do (they alter columns / drop tables). Know which model edits touch the DB.

## 🟠 Still open (not blockers)
- `save()` slug auto-generation is still a no-op: assigns to phantom `self.slug` and slugifies the empty slug instead of the name. "Create without slug → auto-generate" still doesn't work.

## 🟡 Style (batch anytime)
- Field prefixes (`category_name`→`name`); `SlugField` for slugs; `tag`→`tags`; `Meta.ordering`; consistent `related_name` (Enrollment FKs, Course.category/tag have none); optional `UniqueConstraint(['course','order'])` on Lesson.

## Verdict
Topic 1 is functionally done once you migrate. The `save()` no-op and style items are polish. After you migrate + re-run the chain, we move to **Topic 2: ORM** — where this clean schema becomes the playground for query optimization, `select_related`/`prefetch_related`, aggregation, and `annotate`.
