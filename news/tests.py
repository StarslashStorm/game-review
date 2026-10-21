"""
Automated tests for post and comment CRUD.

Supabase is replaced by FakeSupabase (below), a tiny in-memory copy of the
parts of the Supabase client this app uses. Nothing here talks to the real
Supabase project, so running the tests never changes real data.

Run with:  python manage.py test news
"""
import copy
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escapejs


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------

class FakeQuery:
    """Mimics client.table("x").select()/insert()/update()/delete()...execute()."""

    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.action = "select"
        self.payload = None
        self.filters = []
        self.max_rows = None
        self.single_row = False

    # --- what to do ---
    def select(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.action, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.action, self.payload = "update", payload
        return self

    def delete(self):
        self.action = "delete"
        return self

    # --- filters / modifiers ---
    def eq(self, column, value):
        self.filters.append(lambda row: str(row.get(column)) == str(value))
        return self

    def is_(self, column, value):
        if value == "null":
            self.filters.append(lambda row: row.get(column) is None)
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, n):
        self.max_rows = n
        return self

    def range(self, start, end):
        return self

    def single(self):
        self.single_row = True
        return self

    # --- run it ---
    def execute(self):
        rows = self.db.setdefault(self.table, [])
        matches = [row for row in rows if all(f(row) for f in self.filters)]

        if self.action == "insert":
            new_row = {"id": str(uuid.uuid4()), "votes": 0, **self.payload}
            rows.append(new_row)
            return SimpleNamespace(data=[copy.deepcopy(new_row)], count=None)

        if self.action == "update":
            for row in matches:
                row.update(self.payload)
            return SimpleNamespace(data=copy.deepcopy(matches), count=None)

        if self.action == "delete":
            self.db[self.table] = [row for row in rows if row not in matches]
            return SimpleNamespace(data=copy.deepcopy(matches), count=None)

        if self.max_rows is not None:
            matches = matches[:self.max_rows]
        data = copy.deepcopy(matches)
        if self.single_row:
            data = data[0] if data else None
        return SimpleNamespace(data=data, count=len(matches))


class FakeAuth:
    """Any access token starting with "token-" is valid; the rest is the user id."""

    def get_user(self, token):
        if not token.startswith("token-"):
            raise Exception("invalid token")
        return SimpleNamespace(user=SimpleNamespace(id=token[len("token-"):]))


class FakeBucket:
    def upload(self, name, data, options):
        return None

    def get_public_url(self, name):
        return f"https://example.com/{name}"


class FakeSupabase:
    def __init__(self, db):
        self.db = db
        self.auth = FakeAuth()
        self.storage = SimpleNamespace(from_=lambda bucket: FakeBucket())

    def table(self, name):
        return FakeQuery(self.db, name)

    def rpc(self, name, params):
        return SimpleNamespace(execute=lambda: SimpleNamespace(data={"votes": 0}))


# ---------------------------------------------------------------------------
# Shared test setup
# ---------------------------------------------------------------------------

OWNER_ID = str(uuid.uuid4())
OTHER_ID = str(uuid.uuid4())
CREATED = "2026-01-01T12:00:00+00:00"


class SupabaseTestCase(TestCase):
    def setUp(self):
        self.post_id = str(uuid.uuid4())
        self.comment_id = str(uuid.uuid4())
        self.reply_id = str(uuid.uuid4())
        self.sub_reply_id = str(uuid.uuid4())
        self.other_comment_id = str(uuid.uuid4())

        def comment(cid, author, content, parent=None):
            return {
                "id": cid, "news_id": self.post_id, "author_id": author,
                "parent_id": parent, "content": content, "votes": 0,
                "created_at": CREATED, "updated_at": CREATED,
            }

        self.db = {
            "news": [{
                "id": self.post_id,
                "author_id": OWNER_ID,
                "title": "Original title",
                "content": "<p>Original content</p>",
                "image_url": "https://example.com/original.png",
                "votes": 0, "views": 0,
                "created_at": CREATED, "updated_at": CREATED,
            }],
            "comments": [
                comment(self.comment_id, OWNER_ID, "Owner comment"),
                comment(self.reply_id, OTHER_ID, "A reply", parent=self.comment_id),
                comment(self.sub_reply_id, OWNER_ID, "A sub-reply", parent=self.reply_id),
                comment(self.other_comment_id, OTHER_ID, "Someone else's comment"),
            ],
            "categories": [],
            "profiles": [],
        }

        fake = FakeSupabase(self.db)
        for target in ("news.views.get_supabase_client", "accounts.middleware.get_supabase_client"):
            patcher = patch(target, return_value=fake)
            patcher.start()
            self.addCleanup(patcher.stop)

    # --- helpers ---
    def login(self, user_id):
        session = self.client.session
        session["supabase_access_token"] = f"token-{user_id}"
        session["supabase_user_id"] = user_id
        session["user_email"] = "tester@example.com"
        session.save()

    def post_row(self):
        rows = [r for r in self.db["news"] if r["id"] == self.post_id]
        return rows[0] if rows else None

    def comment_row(self, comment_id):
        rows = [r for r in self.db["comments"] if r["id"] == comment_id]
        return rows[0] if rows else None

    def messages_of(self, response):
        return [(m.tags, str(m)) for m in get_messages(response.wsgi_request)]


# ---------------------------------------------------------------------------
# Posts: edit
# ---------------------------------------------------------------------------

class PostUpdateTests(SupabaseTestCase):
    def url(self, pk=None):
        return reverse("news_update", kwargs={"pk": pk or self.post_id})

    def test_owner_sees_prefilled_edit_form(self):
        self.login(OWNER_ID)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "form.html")
        self.assertContains(response, "Edit your post")
        self.assertContains(response, "Save changes")
        self.assertContains(response, 'value="Original title"')
        self.assertContains(response, "&lt;p&gt;Original content&lt;/p&gt;")  # hidden content input
        self.assertContains(response, 'src="https://example.com/original.png"')

    def test_create_page_keeps_create_wording(self):
        self.login(OWNER_ID)
        response = self.client.get(reverse("news_create"))
        self.assertContains(response, "Publish Post")
        self.assertNotContains(response, "Edit your post")

    def test_owner_can_update_post(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(), {"title": "New title", "content": "<p>New content</p>"})
        self.assertRedirects(response, reverse("news_detail", kwargs={"pk": self.post_id}),
                             fetch_redirect_response=False)
        self.assertEqual(self.post_row()["title"], "New title")
        self.assertEqual(self.post_row()["content"], "<p>New content</p>")
        self.assertEqual(self.post_row()["image_url"], "https://example.com/original.png")
        self.assertIn(("success", "Your post was updated."), self.messages_of(response))

    def test_owner_can_remove_image(self):
        self.login(OWNER_ID)
        self.client.post(self.url(), {"title": "T", "content": "<p>C</p>", "remove_image": "true"})
        self.assertIsNone(self.post_row()["image_url"])

    def test_empty_content_is_rejected(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(), {"title": "New title", "content": "<p><br></p>"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Content is required.")
        self.assertEqual(self.post_row()["title"], "Original title")

    def test_empty_title_is_rejected(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(), {"title": "", "content": "<p>Content</p>"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.post_row()["title"], "Original title")

    def test_other_user_cannot_open_edit_page(self):
        self.login(OTHER_ID)
        response = self.client.get(self.url())
        self.assertRedirects(response, reverse("news_detail", kwargs={"pk": self.post_id}),
                             fetch_redirect_response=False)
        self.assertIn(("error", "You can only edit/delete your own posts."), self.messages_of(response))

    def test_other_user_cannot_update(self):
        self.login(OTHER_ID)
        self.client.post(self.url(), {"title": "Hacked", "content": "<p>Hacked</p>"})
        self.assertEqual(self.post_row()["title"], "Original title")

    def test_missing_post_returns_404(self):
        self.login(OWNER_ID)
        response = self.client.get(self.url(pk=str(uuid.uuid4())))
        self.assertEqual(response.status_code, 404)

    def test_logged_out_user_is_sent_to_login(self):
        response = self.client.get(self.url())
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertIn(("info", "Please log in first to do that."), self.messages_of(response))


# ---------------------------------------------------------------------------
# Posts: delete
# ---------------------------------------------------------------------------

class PostDeleteTests(SupabaseTestCase):
    def url(self, pk=None):
        return reverse("news_delete", kwargs={"pk": pk or self.post_id})

    def test_get_shows_confirm_page(self):
        self.login(OWNER_ID)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")
        self.assertContains(response, "Delete this post?")
        self.assertContains(response, "This can't be undone.")
        self.assertContains(response, "Cancel")
        self.assertContains(response, "Yes, delete")
        self.assertIsNotNone(self.post_row())  # nothing deleted yet

    def test_owner_can_delete(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse("news_list"), fetch_redirect_response=False)
        self.assertIsNone(self.post_row())
        self.assertIn(("success", "Your post was deleted."), self.messages_of(response))

    def test_other_user_cannot_delete(self):
        self.login(OTHER_ID)
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse("news_detail", kwargs={"pk": self.post_id}),
                             fetch_redirect_response=False)
        self.assertIsNotNone(self.post_row())
        self.assertIn(("error", "You can only edit/delete your own posts."), self.messages_of(response))

    def test_missing_post_returns_404(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(pk=str(uuid.uuid4())))
        self.assertEqual(response.status_code, 404)

    def test_logged_out_user_cannot_delete(self):
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertIsNotNone(self.post_row())


# ---------------------------------------------------------------------------
# Comments: create
# ---------------------------------------------------------------------------

class CommentCreateTests(SupabaseTestCase):
    def url(self):
        return reverse("comment_create", kwargs={"pk": self.post_id})

    def test_valid_comment_is_saved(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(), {"content": "Nice post!"})
        self.assertRedirects(response, reverse("news_detail", kwargs={"pk": self.post_id}),
                             fetch_redirect_response=False)
        self.assertTrue(any(c["content"] == "Nice post!" for c in self.db["comments"]))
        self.assertIn(("success", "Your comment was posted."), self.messages_of(response))

    def test_empty_comment_is_rejected(self):
        self.login(OWNER_ID)
        before = len(self.db["comments"])
        response = self.client.post(self.url(), {"content": "   "})
        self.assertRedirects(response, reverse("news_detail", kwargs={"pk": self.post_id}),
                             fetch_redirect_response=False)
        self.assertEqual(len(self.db["comments"]), before)
        self.assertIn(("error", "Your comment can't be empty."), self.messages_of(response))

    def test_logged_out_user_cannot_comment(self):
        before = len(self.db["comments"])
        response = self.client.post(self.url(), {"content": "Hi"})
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertEqual(len(self.db["comments"]), before)


# ---------------------------------------------------------------------------
# Comments: edit
# ---------------------------------------------------------------------------

class CommentUpdateTests(SupabaseTestCase):
    def url(self, comment_id=None):
        return reverse("comment_update", kwargs={"comment_id": comment_id or self.comment_id})

    def detail_url(self, comment_id=None):
        return reverse("news_detail", kwargs={"pk": self.post_id}) + f"#comment-{comment_id or self.comment_id}"

    def test_owner_sees_prefilled_edit_form(self):
        self.login(OWNER_ID)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "comment_form.html")
        self.assertContains(response, "Owner comment</textarea>")
        self.assertContains(response, "Save changes")

    def test_owner_can_update_comment(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(), {"content": "Edited comment"})
        self.assertRedirects(response, self.detail_url(), fetch_redirect_response=False)
        self.assertEqual(self.comment_row(self.comment_id)["content"], "Edited comment")
        self.assertIn(("success", "Your comment was updated."), self.messages_of(response))

    def test_owner_can_update_sub_reply(self):
        self.login(OWNER_ID)
        self.client.post(self.url(self.sub_reply_id), {"content": "Edited sub-reply"})
        self.assertEqual(self.comment_row(self.sub_reply_id)["content"], "Edited sub-reply")

    def test_empty_comment_is_rejected(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(), {"content": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your comment can&#x27;t be empty.")
        self.assertEqual(self.comment_row(self.comment_id)["content"], "Owner comment")

    def test_other_user_cannot_edit(self):
        self.login(OTHER_ID)
        response = self.client.post(self.url(), {"content": "Hacked"})
        self.assertRedirects(response, self.detail_url(), fetch_redirect_response=False)
        self.assertEqual(self.comment_row(self.comment_id)["content"], "Owner comment")
        self.assertIn(("error", "You can only edit/delete your own comments."), self.messages_of(response))

    def test_missing_comment_returns_404(self):
        self.login(OWNER_ID)
        response = self.client.get(self.url(str(uuid.uuid4())))
        self.assertEqual(response.status_code, 404)

    def test_logged_out_user_is_sent_to_login(self):
        response = self.client.post(self.url(), {"content": "Hi"})
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertEqual(self.comment_row(self.comment_id)["content"], "Owner comment")


# ---------------------------------------------------------------------------
# Comments: delete
# ---------------------------------------------------------------------------

class CommentDeleteTests(SupabaseTestCase):
    def url(self, comment_id=None):
        return reverse("comment_delete", kwargs={"comment_id": comment_id or self.comment_id})

    def test_get_shows_confirm_page(self):
        self.login(OWNER_ID)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")
        self.assertContains(response, "Delete this comment?")
        self.assertContains(response, "Yes, delete")
        self.assertIsNotNone(self.comment_row(self.comment_id))

    def test_deleting_comment_also_deletes_all_replies(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse("news_detail", kwargs={"pk": self.post_id}),
                             fetch_redirect_response=False)
        self.assertIsNone(self.comment_row(self.comment_id))
        self.assertIsNone(self.comment_row(self.reply_id))
        self.assertIsNone(self.comment_row(self.sub_reply_id))
        # Unrelated comments stay
        self.assertIsNotNone(self.comment_row(self.other_comment_id))
        self.assertIn(("success", "Your comment was deleted."), self.messages_of(response))

    def test_deleting_sub_reply_keeps_parents(self):
        self.login(OWNER_ID)
        self.client.post(self.url(self.sub_reply_id))
        self.assertIsNone(self.comment_row(self.sub_reply_id))
        self.assertIsNotNone(self.comment_row(self.reply_id))
        self.assertIsNotNone(self.comment_row(self.comment_id))

    def test_other_user_cannot_delete(self):
        self.login(OTHER_ID)
        response = self.client.post(self.url())
        self.assertIsNotNone(self.comment_row(self.comment_id))
        self.assertIn(("error", "You can only edit/delete your own comments."), self.messages_of(response))

    def test_missing_comment_returns_404(self):
        self.login(OWNER_ID)
        response = self.client.post(self.url(str(uuid.uuid4())))
        self.assertEqual(response.status_code, 404)

    def test_logged_out_user_cannot_delete(self):
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertIsNotNone(self.comment_row(self.comment_id))


# ---------------------------------------------------------------------------
# Buttons on the detail and list pages
# ---------------------------------------------------------------------------

class DetailPageButtonTests(SupabaseTestCase):
    def get_detail(self):
        return self.client.get(reverse("news_detail", kwargs={"pk": self.post_id}))

    def test_owner_sees_post_and_own_comment_buttons(self):
        self.login(OWNER_ID)
        response = self.get_detail()
        self.assertContains(response, reverse("news_update", kwargs={"pk": self.post_id}))
        self.assertContains(response, reverse("news_delete", kwargs={"pk": self.post_id}))
        # Own top-level comment and own sub-reply
        self.assertContains(response, reverse("comment_update", kwargs={"comment_id": self.comment_id}))
        self.assertContains(response, reverse("comment_delete", kwargs={"comment_id": self.sub_reply_id}))
        # Not on other people's comment or reply
        self.assertNotContains(response, reverse("comment_update", kwargs={"comment_id": self.reply_id}))
        self.assertNotContains(response, reverse("comment_delete", kwargs={"comment_id": self.other_comment_id}))

    def test_other_user_sees_only_their_own_buttons(self):
        self.login(OTHER_ID)
        response = self.get_detail()
        self.assertNotContains(response, reverse("news_update", kwargs={"pk": self.post_id}))
        self.assertNotContains(response, reverse("news_delete", kwargs={"pk": self.post_id}))
        self.assertContains(response, reverse("comment_update", kwargs={"comment_id": self.reply_id}))
        self.assertNotContains(response, reverse("comment_update", kwargs={"comment_id": self.comment_id}))

    def test_logged_out_user_sees_login_box_and_no_buttons(self):
        response = self.get_detail()
        self.assertContains(response, "Log in or create an account to join the conversation")
        self.assertNotContains(response, "What are your thoughts?")
        self.assertNotContains(response, reverse("news_update", kwargs={"pk": self.post_id}))
        self.assertNotContains(response, reverse("comment_update", kwargs={"comment_id": self.comment_id}))


class ListPageTests(SupabaseTestCase):
    def test_logged_in_user_id_is_passed_to_script(self):
        self.login(OWNER_ID)
        response = self.client.get(reverse("news_list"))
        # escapejs writes "-" as "-"; the browser reads it back as the normal id
        self.assertContains(response, f'const currentUserId = "{escapejs(OWNER_ID)}";')
        self.assertContains(response, "post.author_id === currentUserId")

    def test_logged_out_user_gets_empty_id_and_login_notice(self):
        response = self.client.get(reverse("news_list"))
        self.assertContains(response, 'const currentUserId = "";')
        self.assertContains(response, "You need to be logged in to create a post")


# ---------------------------------------------------------------------------
# Messages and the login decorator
# ---------------------------------------------------------------------------

class MessagesAndLoginTests(SupabaseTestCase):
    def test_api_returns_json_401_when_logged_out(self):
        response = self.client.post(reverse("news_api_create"), {"title": "T", "content": "C"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Please log in first to do that."})
        self.assertEqual(len(self.db["news"]), 1)

    def test_vote_api_returns_json_401_when_logged_out(self):
        response = self.client.post(reverse("news_vote", kwargs={"pk": self.post_id}))
        self.assertEqual(response.status_code, 401)

    def test_success_message_is_shown_on_next_page(self):
        self.login(OWNER_ID)
        response = self.client.post(
            reverse("news_update", kwargs={"pk": self.post_id}),
            {"title": "New title", "content": "<p>New</p>"},
            follow=True,
        )
        self.assertContains(response, "Your post was updated.")
        self.assertContains(response, "bg-green-50")

    def test_error_message_is_shown_in_red(self):
        self.login(OTHER_ID)
        response = self.client.get(reverse("news_delete", kwargs={"pk": self.post_id}), follow=True)
        self.assertContains(response, "You can only edit/delete your own posts.")
        self.assertContains(response, "bg-red-50")
