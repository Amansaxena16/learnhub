# Review 03 — Models (runtime-verified)

**Method:** Built the full object chain (User → Instructor → Category → Course → Lesson → Student → Enrollment) in a rolled-back transaction and exercised it.
**Result:**
- ✅ Create chain works — UUID `default=uuid.uuid4` fixed the insert blocker.
- ✅ Duplicate enrollment is **blocked by the DB** when student+course are set — your `UniqueConstraint` fires correctly.
- 🔴 `__str__` crashes: `TypeError: __str__ returned non-string (type User)`.

Legend: 🔴 blocker · 🟠 design · 🟡 style · 🟢 fixed

---

## 🟢 Fixed since Review 02
- UUID PKs generate values (`import uuid` + `default=uuid.uuid4`) — verified by a working `.create()`.
- The `save()` slug method no longer raises (the `if` now reads the real `category_slug`/`tag_slug` field).
- Unique enrollment constraint confirmed working for the normal (non-null) case.

---

## 🔴 Blocker — 1 left

1. **`Instructor.__str__` and `Student.__str__` return `self.user` — a `User` object, not a string.**
   `__str__` **must** return a `str`. Returning a model instance raises `TypeError: __str__ returned non-string` the moment anything calls `str()` on it — admin list pages, the shell, DRF browsable API, error messages, debug toolbar. Proven in the runtime test above.
   *Apply:* return a string built from the user (e.g. the username, or `str(self.user)`). You went from `student_name` (AttributeError) → `self.user` (TypeError); the third time return an actual string.

---

## 🟠 Design — still open (not blockers, but interview-relevant)

2. **`save()` slug auto-generation is silently broken.**
   ```
   if not self.category_slug:
       self.slug = slugify(self.category_slug)
   ```
   It no longer crashes, but it does nothing useful: it assigns to `self.slug` (not a real field — Python just creates an unused attribute), and it slugifies the *slug* (which is empty in this branch) instead of the **name**. So "create a category without a slug and have one generated" does not work — `category_slug` stays empty. Correct intent: *if the slug field is empty, set the slug field from the name field.* Right now it's a no-op that looks like a feature.

3. **`Enrollment` `SET_NULL` + nullable FKs — the constraint has a NULL-shaped hole.**
   The constraint works when both FKs are set (verified). But because they're `null=True` with `on_delete=SET_NULL`, deleting a student/course leaves orphan rows (`student=NULL`), and Postgres allows *many* `(NULL, course)` / `(student, NULL)` rows past the unique constraint. For a join/through model the right design is `CASCADE` + non-null: the link only exists while both ends exist, and the constraint becomes airtight. Decide and justify.

4. **M2M-vs-through contradiction — still unresolved (open since Review 01).**
   `Student.course = ManyToManyField(Course)` and `Enrollment` are still two independent relationships; `status`/`progress`/`enrolled_at` live only in `Enrollment`. Pick one model of the relationship: route the M2M `through="Enrollment"`, or drop the M2M and query `Enrollment`. This is *the* Topic-1 concept — don't leave it half-done.

---

## 🟡 Style — carry-over (won't block interviews-passing, but flagged each round)
- Field-name prefixes (`category_name`/`tag_slug`) → plain `name`/`slug`.
- Slugs → `SlugField`. · `tag` → `tags`. · Add `Meta.ordering` (Course `-created_at`, Lesson `order`).
- `related_name` only on 2 of ~6 relations — make it consistent (`student.enrollments`, `course.enrollments`, etc.).
- Consider `UniqueConstraint(['course','order'])` on `Lesson`.

---

## Verdict
**One real blocker left (`__str__`).** Fix that and Topic 1 is functionally done. Items 2–4 are the difference between "works" and "a senior would sign off on it" — I strongly recommend doing #3 and #4 before we move on, because Enrollment design is exactly what gets probed in interviews. The 🟡 list you can batch-fix anytime.

Fix #1 (and ideally #2–#4), re-run the shell chain, and tell me — then we move to **Topic 2: ORM**.
