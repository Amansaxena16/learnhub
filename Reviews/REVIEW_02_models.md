# Review 02 — Models (after fixes)

**Status:** `manage.py check` → 0 issues. `0001_initial` applied. Schema is valid.
**But:** the app will **crash the first time you create any row.** Migrations validating ≠ runtime working. Two original blockers survive because they fail at *insert* time, not *schema-check* time. Fix those two, then a few design items, and Topic 1 is solid.

Legend: 🔴 blocker · 🟠 design · 🟡 style · 🟢 fixed/good

---

## 🟢 What you fixed correctly

- UUID fields now `primary_key=True, editable=False` ✓
- `Course.instructor` now has `on_delete` ✓
- `auto_now`/`auto_now_add` conflict gone — all `created_at` use `auto_now_add=True` ✓
- `Enrollment.status` has `max_length=20` ✓
- `enrolled_at` → `auto_now_add=True` ✓
- `phone` → `CharField` ✓
- **`Enrollment` now uses `ForeignKey` to Student and Course** (not M2M) ✓ — the core fix
- `Enrollment.progress` added with `MinValueValidator(0)`/`MaxValueValidator(100)` ✓
- `UniqueConstraint(['student','course'])` added ✓ (but see 🟠 #4 — it's currently toothless)
- Instructor/Student now `OneToOneField` to `settings.AUTH_USER_MODEL` ✓ — good pattern choice
- `on_delete` reconsidered: `category`/`instructor` → `SET_NULL` ✓
- `related_name` on `Course.instructor` and `Lesson.course` ✓

Solid progress. Real bugs below.

---

## 🔴 Blockers — `check` passes, but these crash at runtime

1. **UUID primary keys have no `default` — every insert will fail.**
   `id = models.UUIDField(primary_key=True, editable=False, unique=True, null=False, blank=False)`
   There is no `default`. With `editable=False` and no default, Django has no value to put in the PK when you create an object → `IntegrityError`/null PK on the very first `.create()`. Schema migration succeeds (the column exists); inserting data does not.
   *Apply:* give it a callable default that generates a UUID, and `import uuid` at the top (currently not imported). Verify with: open `manage.py shell`, try to create one `Category` — it must save without you passing an `id`.

2. **The `save()` slug bug is still here — just moved.**
   ```
   if not self.slug:
       self.slug = slugify(self.category_slug)
   ```
   You changed the *argument* to `slugify()`, but `self.slug` (both the `if` check and the assignment target) is still a field that doesn't exist on this model — the field is `category_slug`. `if not self.slug` raises `AttributeError` the moment any `Category` is saved. Same bug in `Tag` (`self.slug` / `tag_slug`).
   Also the *logic* is inverted: you slugify a **name into a slug**, not the slug into itself. Think: "if the slug is empty, build it from the name." Check the right field, assign to the right field.
   *(This bug has now survived two rounds purely because of the `category_`/`tag_` field-name prefixes. That's your sign to drop them — see 🟡 #7.)*

---

## 🟠 Design issues still open

3. **`Student.student_name` no longer exists, but `__str__` still returns it.**
   `Student.__str__` returns `self.student_name`; you replaced that field with `user`. Any time a `Student` is displayed (admin list, shell `repr`, error messages) → `AttributeError`. Return something off `self.user` instead.

4. **`UniqueConstraint` is currently toothless because the FKs are nullable.**
   `Enrollment.student` and `course` are `null=True`, and Postgres treats `NULL` as distinct from every other `NULL`. So `(student, course)` unique does **not** block duplicates when either side is null, and your "a student can't enroll twice" guarantee has a hole. This ties directly to #5.

5. **`Enrollment` FKs as `SET_NULL` is the wrong choice for a join/through model.**
   An enrollment row only has meaning while *both* its student and course exist. With `SET_NULL` you'd keep orphaned rows like "enrollment for (no student) in (no course)" — garbage link rows. The standard choice for a through/link model is `CASCADE`: when either endpoint is deleted, the link disappears. Switching to `CASCADE` also lets you make the FKs non-null, which **restores the teeth of the unique constraint** in #4. Decide and justify.

6. **The M2M-vs-through contradiction from Review 01 is still unresolved.**
   `Student.course = models.ManyToManyField(Course)` still exists *and* `Enrollment` exists as a separate table. They're still two independent relationships, and your rich data (`status`, `progress`, `enrolled_at`) lives in `Enrollment`, which the M2M doesn't know about. You must pick one:
   - make the M2M go *through* the enrollment model so they're the same relationship (then `student.course.all()` and the enrollment data are linked), **or**
   - drop the M2M field and always go through the `Enrollment` model directly.
   Be able to explain why having both is wrong.

---

## 🟡 Style / idiom still open (carry-over from Review 01)

7. **Drop the model-name field prefixes** (`category_name`→`name`, `tag_slug`→`slug`, …). They've now directly caused bug #2 twice.
8. **Slugs should be `SlugField`**, not `CharField`.
9. **`tag` → `tags`** (it's a many relationship).
10. **No `Meta.ordering`** on `Course` (`-created_at`) or `Lesson` (`order`).
11. **`related_name` is inconsistent** — present on `Course.instructor`/`Lesson.course`, missing on `Course.category`, `Course.tag`, `Student.course`, `Enrollment.student`, `Enrollment.course`. Add everywhere so reverse lookups read well (e.g. `student.enrollments.all()`).
12. **`Lesson` still allows duplicate `order` within a course** — consider `UniqueConstraint(['course','order'])`.
13. **Redundant flags on UUID PK:** `unique=True, null=False, blank=False` are all implied by `primary_key=True`. Harmless, but noise.

---

## Re-fix checklist

- [ ] 🔴 Add a UUID-generating `default` to every PK + `import uuid` — then prove a `.create()` works in the shell
- [ ] 🔴 Fix both `save()` methods: check/assign the *real* slug field, built from the *name* field
- [ ] 🟠 Fix `Student.__str__`
- [ ] 🟠 `Enrollment` FKs → `CASCADE` + non-null, so the unique constraint actually bites
- [ ] 🟠 Resolve M2M-vs-through (pick one model of the relationship)
- [ ] 🟡 Drop prefixes · `SlugField` · `tags` · `Meta.ordering` · consistent `related_name` · `(course, order)` constraint

---

## Prove it works (do this before resubmitting)

Migrations passing isn't proof. In `manage.py shell`, create a `User` → `Instructor` → `Category` → `Course` → two `Lesson`s → a `Student` → an `Enrollment`. Then try to create the **same** enrollment twice and confirm the DB rejects it. If all of that works, Topic 1 is genuinely done.

---

## Interview follow-ups (new, building on Review 01)

1. Why does `manage.py check` pass but inserting a row still fail? (Schema validation vs runtime/data constraints.)
2. In Postgres, how are `NULL`s treated in a unique constraint, and how does that affect a nullable composite unique key?
3. For a join table, why is `CASCADE` usually right and `SET_NULL` usually wrong?
4. `OneToOneField` to `User` (profile pattern) vs a custom `AbstractUser` — when would you choose each?
5. Where should slug generation live — `save()`, the serializer, a signal, or the form? Trade-offs?
