import uuid
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import News
from .forms import NewsForm, CommentForm
from core.supabase import get_supabase_client
from datetime import datetime
from accounts.decorator import supabase_auth_required
from core.utils import parse_supabase_data

def get_row_or_404(client, table, row_id):
    """Fetch one row by id from a Supabase table, or raise Http404."""
    res = client.table(table).select("*").eq("id", str(row_id)).limit(1).execute()
    if not res.data:
        raise Http404(f"{table} not found")
    return res.data[0]


def is_owner(request, row):
    """True when the logged-in user wrote this post/comment."""
    return str(row.get("author_id")) == str(request.session.get("supabase_user_id"))


def news_list(request):
    res = (
        get_supabase_client()
        .table("news")
        .select("*, profiles(username), categories(name)")  
        .order("created_at", desc=True)
        .execute()
    )
    
    categories = get_supabase_client().table("categories").select("*").execute()

    news = []
    for item in res.data or []:
        profile = item.pop("profiles", None)
        category = item.pop("categories", None)
        item["author_username"] = profile["username"] if profile else "Unknown"
        item["category_name"] = category["name"] if category else "Uncategorized"

        for field in ("created_at", "updated_at"):
            raw = item.get(field)
            if raw:
                item[field] = datetime.fromisoformat(raw)

        news.append(item)

    return render(request, "list.html", {
        "title":       "Web Game News",
        "description": "Browse the latest news posts.",
        "news":        news,
        "categories": categories.data
    })

def news_detail(request, pk):
    client = get_supabase_client()

    # ========================
    # 🔥 VIEW COUNT LOGIC
    # ========================
    viewed_key = f"viewed_news_{pk}"

    if not request.session.get(viewed_key):
        try:
            client.rpc("increment_news_views", {"news_id": str(pk)}).execute()
            request.session[viewed_key] = True
        except Exception as e:
            print("View increment failed:", e)

    # ========================
    # 📄 FETCH NEWS
    # ========================
    res = (
        client.table("news")
        .select("*, profiles(username, avatar_url)")
        .eq("id", str(pk))
        .single()
        .execute()
    )

    if not res.data:
        raise Http404("News not found")

    item = res.data
    profile = item.pop("profiles", None)

    item["author_username"] = profile["username"] if profile else "Unknown"
    item["author_avatar"] = profile.get("avatar_url") if profile else None
    item = parse_supabase_data(item, "created_at", "updated_at")

    # ========================
    # 🔁 RECURSIVE REPLIES (3 LEVEL)
    # ========================
    def fetch_replies(parent_id, depth=1, max_depth=3):
        if depth > max_depth:
            return []

        replies_res = (
            client.table("comments")
            .select("*, profiles(username, avatar_url)")
            .eq("parent_id", parent_id)
            .order("votes", desc=True)
            .order("created_at", desc=True)
            .execute()
        )

        replies = []
        for reply in (replies_res.data or []):
            r_profile = reply.pop("profiles", None)

            reply["author_username"] = r_profile["username"] if r_profile else "Unknown"
            reply["author_avatar"] = r_profile.get("avatar_url") if r_profile else None

            reply = parse_supabase_data(reply, "created_at", "updated_at")

            # recursive (max 3 level)
            reply["replies"] = fetch_replies(reply["id"], depth + 1, max_depth)

            replies.append(reply)

        return replies

    # ========================
    # 💬 TOP LEVEL COMMENTS
    # ========================
    comments_res = (
        client.table("comments")
        .select("*, profiles(username, avatar_url)")
        .eq("news_id", str(pk))
        .is_("parent_id", "null")
        .order("votes", desc=True)
        .order("created_at", desc=True)
        .execute()
    )

    comments = []

    for comment in (comments_res.data or []):
        profile = comment.pop("profiles", None)

        comment["author_username"] = profile["username"] if profile else "Unknown"
        comment["author_avatar"] = profile.get("avatar_url") if profile else None

        comment = parse_supabase_data(comment, "created_at", "updated_at")

        # start from level 2
        comment["replies"] = fetch_replies(comment["id"], depth=2)

        comments.append(comment)

    # ========================
    # 🔢 COUNT COMMENTS
    # ========================
    def count_comments(nodes):
        total = 0
        for n in nodes:
            total += 1
            total += count_comments(n.get("replies", []))
        return total

    return render(
        request,
        "detail.html",
        {
            "item": item,
            "comments": comments,
            "comments_count": count_comments(comments),
        },
    )

@supabase_auth_required
def news_create(request):
    if request.method == 'POST':
        form = NewsForm(request.POST)
        if form.is_valid():
            user_id = request.session.get('supabase_user_id')
            
            get_supabase_client().table('news').insert({
                'title': form.cleaned_data['title'],
                'content': form.cleaned_data['content'],
                'author_id': user_id,
            }).execute()
            return redirect('news_list')
    else:
        form = NewsForm()
    return render(request, 'form.html', {
        "title": "Create - Web Game News",
        "description": "Create a new news post.",
        'form': form
    })

def news_api(request):
    category_id = request.GET.get("category_id", "all")
    page        = int(request.GET.get("page", 1))
    page_size   = 10

    offset = (page - 1) * page_size
    client = get_supabase_client()

    count_query = client.table("news").select("*", count="exact", head=True)
    if category_id and category_id != "all":
        count_query = count_query.eq("category_id", category_id)
        
    count_res   = count_query.execute()
    total       = count_res.count or 0

    query = client.table("news").select("*, profiles(username), categories(name)")
    if category_id and category_id != "all":
        query = query.eq("category_id", category_id)

    query = query.order("created_at", desc=True)

    res = query.range(offset, offset + page_size - 1).execute()

    news = []
    for item in (res.data or []):
        profile = item.pop("profiles", None)
        category = item.pop("categories", None)
        item["author_username"] = profile["username"] if profile else "Unknown"
        item["category_name"] = category["name"] if category else "Uncategorized"
        news.append(item)

    return JsonResponse({
        "news":     news,
        "page":     page,
        "has_more": (offset + page_size) < total,
    })

@supabase_auth_required
def news_api_create(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    title       = (request.POST.get("title") or "").strip()
    category_id = request.POST.get("category_id")
    content     = (request.POST.get("content") or "").strip()
    image       = request.FILES.get("image")
    user_id     = request.session.get("supabase_user_id")

    if not user_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if not title:
        return JsonResponse({"error": "Title is required"}, status=400)
    if not content:
        return JsonResponse({"error": "Content is required"}, status=400)

    supabase = get_supabase_client()

    image_url = None
    if image:
        file_ext  = image.name.rsplit(".", 1)[-1].lower()
        file_name = f"{uuid.uuid4()}.{file_ext}"
        try:
            supabase.storage.from_("news_bucket").upload(
                file_name,
                image.read(),
                {"content-type": image.content_type},
            )
            image_url = supabase.storage.from_("news_bucket").get_public_url(file_name)
        except Exception as e:
            return JsonResponse({"error": f"Image upload failed: {str(e)}"}, status=500)

    try:
        result = supabase.table("news").insert({
            "title":     title,
            "content":   content,
            "author_id": user_id,
            "category_id": category_id,
            "image_url": image_url,
        }).execute()
    except Exception as e:
        return JsonResponse({"error": f"Database insert failed: {str(e)}"}, status=500)

    if not result.data:
        return JsonResponse({"error": "Insert returned no data"}, status=500)

    return JsonResponse({"success": True, "message": "News created successfully"})

@supabase_auth_required
@require_http_methods(["GET", "POST"])
def news_update(request, pk):
    client = get_supabase_client()
    news   = get_row_or_404(client, "news", pk)

    if not is_owner(request, news):
        messages.error(request, "You can only edit/delete your own posts.")
        return redirect("news_detail", pk=pk)

    context = {
        "news": news,
        "is_edit": True,
        "title": "Edit - Web Game News",
        "description": "Edit your news post.",
    }

    if request.method == "GET":
        context["form"] = NewsForm(initial={
            "title":   news["title"],
            "content": news["content"],
        })
        return render(request, "form.html", context)

    form = NewsForm(request.POST, request.FILES)
    context["form"] = form

    if not form.is_valid():
        return render(request, "form.html", context)

    image        = form.cleaned_data.get("image")
    image_url    = news.get("image_url")
    remove_image = request.POST.get("remove_image") == "true"

    if image:
        file_ext  = image.name.rsplit(".", 1)[-1].lower()
        file_name = f"{uuid.uuid4()}.{file_ext}"
        try:
            client.storage.from_("news_bucket").upload(
                file_name,
                image.read(),
                {"content-type": image.content_type},
            )
            image_url = client.storage.from_("news_bucket").get_public_url(file_name)
        except Exception as e:
            form.add_error(None, f"Image upload failed: {str(e)}")
            return render(request, "form.html", context)
    elif remove_image:
        image_url = None

    try:
        result = (
            client.table("news")
            .update({
                "title":     form.cleaned_data["title"],
                "content":   form.cleaned_data["content"],
                "image_url": image_url,
            })
            .eq("id", str(pk))
            .execute()
        )
    except Exception as e:
        form.add_error(None, f"Update failed: {str(e)}")
        return render(request, "form.html", context)

    if not result.data:
        form.add_error(None, "Update returned no data, please try again.")
        return render(request, "form.html", context)

    messages.success(request, "Your post was updated.")
    return redirect("news_detail", pk=pk)


@supabase_auth_required
@require_http_methods(["GET", "POST"])
def news_delete(request, pk):
    client = get_supabase_client()
    news   = get_row_or_404(client, "news", pk)

    if not is_owner(request, news):
        messages.error(request, "You can only edit/delete your own posts.")
        return redirect("news_detail", pk=pk)

    if request.method == "GET":
        return render(request, "confirm_delete.html", {
            "title": "Delete post - Web Game News",
            "object_type": "post",
            "object_preview": news["title"],
            "cancel_url": reverse("news_detail", kwargs={"pk": pk}),
        })

    client.table("news").delete().eq("id", str(pk)).execute()
    messages.success(request, "Your post was deleted.")
    return redirect("news_list")


@supabase_auth_required
def news_vote(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    user_id = request.session.get("supabase_user_id")
    client  = get_supabase_client()

    import json
    try:
        body  = json.loads(request.body)
        value = body.get("value")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if value not in (1, 0, -1):
        return JsonResponse({"error": "Value must be 1, 0, or -1"}, status=400)

    try:
        result = client.rpc("handle_vote", {
            "p_news_id": str(pk),
            "p_user_id": user_id,
            "p_value":   value,
        }).execute()

        new_votes = result.data.get("votes") 

    except Exception as e:
        return JsonResponse({"error": f"Vote failed: {str(e)}"}, status=500)

    return JsonResponse({"success": True, "votes": new_votes})


@supabase_auth_required
def comment_create(request, pk):
    if request.method != "POST":
        return redirect("news_detail", pk=pk)

    user_id = request.session.get("supabase_user_id")
    client = get_supabase_client()

    form = CommentForm(request.POST)
    parent_id = request.POST.get("parent_id")

    if not form.is_valid():
        messages.error(request, form.errors["content"][0])
        return redirect("news_detail", pk=pk)

    try:
        depth = 1

        if parent_id:
            parent = client.table("comments") \
                .select("id,parent_id") \
                .eq("id", parent_id) \
                .single() \
                .execute()

            if parent.data:
                if parent.data["parent_id"]:
                    # parent is level 2 → this would be level 3
                    depth = 3
                else:
                    # parent is root → this is level 2
                    depth = 2

        if depth > 3:
            messages.error(request, "Maximum reply depth reached.")
            return redirect("news_detail", pk=pk)

        result = client.table("comments").insert({
            "news_id": str(pk),
            "author_id": user_id,
            "parent_id": parent_id if parent_id else None,
            "content": form.cleaned_data["content"],
        }).execute()

    except Exception:
        messages.error(request, "Something went wrong posting your comment. Please try again.")
        return redirect("news_detail", pk=pk)

    if not result.data:
        messages.error(request, "Something went wrong posting your comment. Please try again.")
        return redirect("news_detail", pk=pk)

    messages.success(request, "Your comment was posted.")
    return redirect("news_detail", pk=pk)


def comment_redirect(comment):
    """Send the user back to the post, scrolled to this comment."""
    url = reverse("news_detail", kwargs={"pk": comment["news_id"]})
    return redirect(f"{url}#comment-{comment['id']}")


@supabase_auth_required
@require_http_methods(["GET", "POST"])
def comment_update(request, comment_id):
    client  = get_supabase_client()
    comment = get_row_or_404(client, "comments", comment_id)

    if not is_owner(request, comment):
        messages.error(request, "You can only edit/delete your own comments.")
        return comment_redirect(comment)

    if request.method == "GET":
        form = CommentForm(initial={"content": comment["content"]})
    else:
        form = CommentForm(request.POST)
        if form.is_valid():
            client.table("comments") \
                .update({"content": form.cleaned_data["content"]}) \
                .eq("id", str(comment_id)) \
                .execute()
            messages.success(request, "Your comment was updated.")
            return comment_redirect(comment)

    return render(request, "comment_form.html", {
        "title": "Edit comment - Web Game News",
        "form": form,
        "comment": comment,
        "cancel_url": reverse("news_detail", kwargs={"pk": comment["news_id"]}),
    })


@supabase_auth_required
@require_http_methods(["GET", "POST"])
def comment_delete(request, comment_id):
    client  = get_supabase_client()
    comment = get_row_or_404(client, "comments", comment_id)

    if not is_owner(request, comment):
        messages.error(request, "You can only edit/delete your own comments.")
        return comment_redirect(comment)

    if request.method == "GET":
        return render(request, "confirm_delete.html", {
            "title": "Delete comment - Web Game News",
            "object_type": "comment",
            "object_preview": comment["content"],
            "cancel_url": reverse("news_detail", kwargs={"pk": comment["news_id"]}),
        })

    # Collect the comment and every reply below it (replies of replies too).
    ids_to_delete = [str(comment_id)]
    index = 0
    while index < len(ids_to_delete):
        children = client.table("comments") \
            .select("id") \
            .eq("parent_id", ids_to_delete[index]) \
            .execute()
        ids_to_delete += [str(child["id"]) for child in (children.data or [])]
        index += 1

    # Delete the deepest replies first and the comment itself last.
    for row_id in reversed(ids_to_delete):
        client.table("comments").delete().eq("id", row_id).execute()

    messages.success(request, "Your comment was deleted.")
    return redirect("news_detail", pk=comment["news_id"])


@supabase_auth_required
def comment_vote(request, comment_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    user_id = request.session.get("supabase_user_id")
    client  = get_supabase_client()
    
    import json
    try:
        body  = json.loads(request.body)
        value = body.get("value")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request body"}, status=400)
    
    if value not in (1, 0, -1):
        return JsonResponse({"error": "Value must be 1, 0, or -1"}, status=400)
    
    try:
        result = client.rpc("handle_comment_vote", {
            "p_comment_id": str(comment_id),
            "p_user_id":    user_id,
            "p_value":      value,
        }).execute()
        
        new_votes = result.data.get("votes")
    except Exception as e:
        return JsonResponse({"error": f"Vote failed: {str(e)}"}, status=500)
    
    return JsonResponse({"success": True, "votes": new_votes})