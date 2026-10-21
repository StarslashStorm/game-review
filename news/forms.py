from django import forms


class NewsForm(forms.Form):
    title = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={
            "placeholder": "Give your post a headline...",
            "class": (
                "w-full bg-gray-50 border border-gray-100 rounded-2xl px-5 py-3.5 "
                "text-sm font-medium text-gray-800 placeholder-gray-300 "
                "focus:outline-none focus:bg-white focus:border-orange-300 "
                "focus:ring-4 focus:ring-orange-50 transition-all"
            ),
        })
    )
    content = forms.CharField(
        required=False,                          # ✅ Quill fills this on submit
        widget=forms.HiddenInput(attrs={"id": "content"})
    )
    image = forms.ImageField(required=False)

    def clean_content(self):
        content = self.cleaned_data.get("content", "").strip()
        # Strip empty Quill output
        if not content or content == "<p><br></p>":
            raise forms.ValidationError("Content is required.")
        return content

class CommentForm(forms.Form):
    content = forms.CharField(
        strip=True,  # "   " becomes "" and is rejected as empty
        error_messages={"required": "Your comment can't be empty."},
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "What are your thoughts?",
            "class": (
                "w-full bg-gray-50 border border-gray-200 rounded-2xl p-4 text-sm "
                "focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 "
                "transition-all outline-none resize-none"
            ),
        }),
    )
