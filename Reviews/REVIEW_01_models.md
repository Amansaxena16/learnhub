# Review 01 — Models

**Scope:** `courses/models.py` + `settings.py`
**Verdict:** Does **not** migrate yet. Multiple `makemigrations`/`migrate`-blocking errors. Relationship *intent* is mostly right; execution has bugs. Fix the blockers first, then the design issues, then resubmit.

Legend: 🔴 blocker (breaks migrate/runtime) · 🟠 design mistake (interview-relevant) · 🟡 style/idiom · 🟢 done well

---

## 🔴 Blockers — these stop the project from running

1. **UUID `id` is not a primary key.**
   Every model has `id = models.UUIDField(unique=True, null=False, blank=False)`. This is missing `primary_key=True`, a `default`, and `editable=False`.
   - No field is marked `primary_key=True`, so Django tries to auto-create its own `id` field — but the name `id` is already taken → system-check/migration failure.
   - No `default` → every single insert would require you to hand-generate a UUID.
   - `uuid` is never imported.
   *Concept to apply:* a UUID PK needs `primary_key=True`, a callable default that generates the value, and should not be user-editable. `unique=True` becomes redundant once it's the PK. Decide: do you even want UUIDs here, or is the default `BigAutoField` fine? Be ready to justify in an interview (UUIDs: no enumeration/no sequential leak, harder to guess; cost: 16 bytes, worse index locality).

2. **`save()` references fields that don't exist.**
   `Category.save()` does `if not self.slug: self.slug = slugify(self.name)`, but your fields are named `category_slug` and `category_name`. `self.slug` / `self.name` don't exist → `AttributeError` on every save. Same bug in `Tag`. (This is also a strong argument for *not* prefixing field names with the model name — see 🟡 #14.)

3. **`Course.instructor` ForeignKey has no `on_delete`.**
   `instructor = models.ForeignKey(Instructor)` — `on_delete` is required. Migration will raise `TypeError`.

4. **`auto_now=True` AND `auto_now_add=True` on the same field.**
   On `Instructor.created_at`, `Course.created_at`, `Lesson.created_at`, `Student.created_at`. These are mutually exclusive and Django will error. Know the difference:
   - `auto_now_add=True` → set once, at creation (this is what `created_at` wants).
   - `auto_now=True` → overwritten on *every* save (this is what an `updated_at` field wants).

5. **`status = CharField(choices=STATUS, ...)` has no `max_length`.**
   `CharField` requires `max_length` → system-check error. Pick a length that fits your longest choice key (`completed`).

6. **`Enrollment.enrolled_at` uses `auto_created=True`.**
   `auto_created` is an internal Django attribute, not a field option you set. You want `auto_now_add=True` only.

7. **`Student.phone = IntegerField(max_length=10)`.**
   `IntegerField` ignores `max_length` and is the wrong type for a phone number (drops leading zeros, can't hold `+`/country code, overflows). Phone numbers are *text*, not quantities — use a `CharField` with validation.

---

## 🟠 Relationship design — this is the heart of Topic 1, read carefully

8. **`Enrollment` is modeled completely wrong — this is the most important fix.**
   You wrote:
   - `student = models.ManyToManyField(Student)`
   - `course = models.ManyToManyField(Course)`

   An **enrollment row represents exactly one student in exactly one course.** Using `ManyToManyField` says "one enrollment links to many students *and* many courses," which is nonsensical. A through/join model points to each side with a **`ForeignKey`**, not M2M. Think: one enrollment → one student, one course, plus its own data.

   Also missing from `Enrollment`: the **`progress` (0–100)** field the spec required.

9. **Your `Enrollment` through-model and `Student.course` M2M contradict each other.**
   You created `Student.course = models.ManyToManyField(Course)` (which auto-builds a hidden join table) **and** a separate `Enrollment` model. So you now have *two* unrelated ways to link students and courses, and the extra data (`status`, `enrolled_at`, `progress`) lives in a table nothing points to.
   *Concept:* when an M2M relationship carries its own attributes, you wire it as `ManyToManyField(Course, through="Enrollment")` so the M2M and the through-model are the *same* relationship — or you drop the M2M field entirely and just query `Enrollment` directly. Pick one and be able to explain the trade-off. You must not have both as independent things.

10. **No duplicate-enrollment guard.**
    The spec required: a student can't enroll in the same course twice, enforced at the DB level. There is no `UniqueConstraint` / `unique_together` on `(student, course)` in `Enrollment`. Right now the DB happily allows duplicates. This is a classic interview point — application-level checks race; the *database* constraint is the source of truth.

11. **`Instructor` and `Student` reinvent `User` instead of using Django auth.**
    The spec said instructor and student are `User`s. You built standalone models duplicating `name`/`email`. Consequences: no passwords, no login, no permissions, and you'll fight this hard when we reach Authentication/Permissions later. Two standard patterns to know:
    - FK/`OneToOneField` to `settings.AUTH_USER_MODEL` (a "profile" alongside the built-in `User`), or
    - a custom user model (`AbstractUser`) set as `AUTH_USER_MODEL`.
    For a mid-level interview you should at minimum link to `User` rather than recreate it. Decide which pattern and why.

12. **`on_delete` choices need justifying — you defaulted to CASCADE.**
    - `Course.category` → `CASCADE`: deleting one category (e.g. "Web Development") would delete *every course in it*. Almost certainly wrong. Consider `PROTECT` (block deletion) or `SET_NULL` (keep course, clear category — requires `null=True`).
    - `Course.instructor` → currently missing (blocker #3). When you add it: should deleting an instructor delete all their courses? Probably `PROTECT` or `SET_NULL`, not `CASCADE`.
    - `Lesson.course` → `CASCADE`: ✅ correct, lessons have no meaning without their course.
    - `Enrollment` FKs → `CASCADE` on both is reasonable (the link dies with either side). Be ready to say so.
    *In an interview, "I used CASCADE everywhere" is a red flag. Each FK is a deliberate decision.*

13. **Missing `related_name` everywhere (spec explicitly required it).**
    Without it you're stuck with `_set` reverse accessors. Add meaningful ones so you can write `instructor.courses.all()`, `course.lessons.all()`, `category.courses.all()`, `course.tags.all()`. Name them from the *reverse* direction's point of view.

---

## 🟡 Style / idiom — won't break, but interviewers notice

14. **Stop prefixing field names with the model name.**
    `category_name`, `category_slug`, `tag_name`, `tag_slug` → just `name`, `slug`. You already say `Category.objects` / `category.`, so `category.category_name` is redundant stutter. (Bonus: this is exactly what caused bug #2.)

15. **Use `SlugField`, not `CharField`, for slugs.**
    `SlugField` validates the slug character set and is indexed-by-intent. Pair it with `unique=True`.

16. **`tag` should be plural: `tags`.**
    It's a `ManyToManyField` — a course has many tags. Field name should read as a collection.

17. **No `Meta.ordering` anywhere (spec asked for it).**
    `Lesson` clearly wants `ordering = ['order']`. `Course` probably `['-created_at']`. Without it, query results have no guaranteed order.

18. **Consider `unique_together`/`UniqueConstraint` on `(course, order)` for `Lesson`.**
    Otherwise two lessons in the same course can both be "order 1."

19. **`description = TextField(max_length=500)`** — `max_length` on `TextField` is only enforced by forms, not the database. If you truly want a hard cap, that's a `CharField` or a `CheckConstraint`/validator. Decide if the cap is real.

20. **`__str__` returning the slug** for `Category`/`Tag` — prefer the human-readable name; slugs are for URLs. Minor.

21. **`price`** — consider a non-negative validator (`MinValueValidator(0)`); a negative course price should be impossible.

---

## 🟢 What you did well

- **`settings.py` uses `django-environ`** and pulls DB credentials from the environment instead of hardcoding them. This is genuinely better than most mid-level submissions. (Next step: move `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` into env too — right now `SECRET_KEY` is still the insecure generated default and `DEBUG=True` is hardcoded.)
- **PostgreSQL engine configured correctly**, as planned.
- **`Enrollment.STATUS` as a list of `(value, label)` choices** — correct shape and naming.
- **You reached for a through-model (`Enrollment`) at all** — the *instinct* to put enrollment data in its own table is exactly right; the wiring (#8/#9) is what's off.
- **`Lesson.course` CASCADE and `PositiveIntegerField` for `order`** — both correct, deliberate choices.
- **Docstring examples** in models showing sample data — nice for a learning project.

---

## Fix checklist before you resubmit

- [ ] UUID PKs: `primary_key=True` + generated default + `editable=False` + import `uuid` (or switch to default PK and justify)
- [ ] Fix both `save()` methods to use the real field names
- [ ] Add `on_delete` to `Course.instructor`
- [ ] Remove the `auto_now`+`auto_now_add` conflict on all four `created_at` fields
- [ ] Add `max_length` to `Enrollment.status`
- [ ] Fix `Enrollment.enrolled_at` (`auto_now_add` only)
- [ ] `phone` → `CharField` with validation
- [ ] Rebuild `Enrollment`: FKs to Student & Course (not M2M) + add `progress`
- [ ] Resolve the M2M-vs-through contradiction (`through="Enrollment"` or drop the M2M)
- [ ] Add `UniqueConstraint`/`unique_together` on `(student, course)`
- [ ] Link Instructor/Student to Django's `User` (pick a pattern)
- [ ] Reconsider every `on_delete` (esp. `Course.category`)
- [ ] Add `related_name` to all relations
- [ ] Drop the model-name prefixes; use `SlugField`; pluralize `tags`
- [ ] Add `Meta.ordering`

When migrations run clean (`python manage.py makemigrations && migrate` with zero errors), tell me and I'll re-review the corrected version.

---

## Interview follow-ups to be ready for (Topic 1)

1. What's the difference between `null=True` and `blank=True`? (DB vs validation layer — you set both on many fields; know why.)
2. When do you need a `through` model vs a plain `ManyToManyField`?
3. `on_delete=CASCADE` vs `PROTECT` vs `SET_NULL` vs `SET_DEFAULT` — give a real scenario for each.
4. Why is a DB-level unique constraint safer than checking "does this enrollment exist?" in your view? (Race conditions.)
5. UUID PK vs auto-increment PK — trade-offs.
6. What does `related_name` change, and what's `related_query_name`?
7. `auto_now` vs `auto_now_add` — and how would you store both created and updated timestamps?
