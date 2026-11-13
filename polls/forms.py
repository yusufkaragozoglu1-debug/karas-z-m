from datetime import timedelta

from django import forms
from django.db import transaction
from django.utils import timezone

from .models import Option, Poll

MAX_OPTIONS = 5
MIN_OPTIONS = 2
OPTION_FIELDS = [f"option_{i}" for i in range(1, MAX_OPTIONS + 1)]

# value (hours; "" = no limit) -> label
DURATION_CHOICES = [
    ("", "Süresiz"),
    ("1", "1 saat"),
    ("24", "24 saat"),
    ("72", "3 gün"),
    ("168", "7 gün"),
]


class PollCreateForm(forms.ModelForm):
    duration = forms.ChoiceField(
        label="Ne kadar açık kalsın?",
        choices=DURATION_CHOICES,
        required=False,
        error_messages={"invalid_choice": "Geçerli bir süre seç."},
    )

    class Meta:
        model = Poll
        fields = ("question", "description")
        labels = {"question": "Sorun ne?", "description": "Açıklama (isteğe bağlı)"}
        widgets = {
            "question": forms.TextInput(attrs={"placeholder": "Pizza mı, hamburger mi?", "autofocus": True}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "İstersen biraz detay ver…"}),
        }
        error_messages = {
            "question": {
                "required": "Bir soru yazmalısın.",
                "max_length": "Soru en fazla 200 karakter olabilir.",
            },
            "description": {"max_length": "Açıklama en fazla 500 karakter olabilir."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for index, name in enumerate(OPTION_FIELDS, start=1):
            self.fields[name] = forms.CharField(
                label=f"Seçenek {index}",
                max_length=80,
                required=index <= MIN_OPTIONS,
                error_messages={
                    "required": "Bu seçenek zorunlu.",
                    "max_length": "Seçenek en fazla 80 karakter olabilir.",
                },
                widget=forms.TextInput(attrs={"placeholder": f"Seçenek {index}"}),
            )

    def clean_question(self):
        question = self.cleaned_data["question"].strip()
        if not question:
            raise forms.ValidationError("Bir soru yazmalısın.")
        return question

    def clean_description(self):
        return self.cleaned_data["description"].strip()

    def clean(self):
        cleaned = super().clean()
        seen = {}
        for name in OPTION_FIELDS:
            value = " ".join((cleaned.get(name) or "").split())
            if name in cleaned:
                cleaned[name] = value
            if not value:
                if name in ("option_1", "option_2") and name not in self.errors:
                    self.add_error(name, "Bu seçenek zorunlu.")
                continue
            key = value.casefold()
            if key in seen:
                self.add_error(name, "Aynı seçeneği iki kez yazamazsın.")
            else:
                seen[key] = name
        return cleaned

    def get_options(self):
        """Filled option texts in field order."""
        return [self.cleaned_data[name] for name in OPTION_FIELDS if self.cleaned_data.get(name)]

    @transaction.atomic
    def save(self, author):
        poll = super().save(commit=False)
        poll.author = author
        hours = self.cleaned_data.get("duration")
        if hours:
            poll.closes_at = timezone.now() + timedelta(hours=int(hours))
        poll.save()
        Option.objects.bulk_create(
            [Option(poll=poll, text=text, order=index) for index, text in enumerate(self.get_options())]
        )
        return poll
