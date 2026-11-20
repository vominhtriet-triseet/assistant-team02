"""Replies in the student's language: Vietnamese when the message has Vietnamese letters, else English.

Call sites keep the English text as the key, so the code stays readable:
    t(lang, "Saved note #{id}: {title}.", id=3, title="Derivatives")
Long texts use a short key with the English version in EN.
"""
from __future__ import annotations

import re

VI_LETTERS = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.I)
UNACCENTED_VI = {"xin chao", "chao", "chao ban", "giup", "huong dan"}


def detect(text: str, previous: str = "en") -> str:
    """'vi' or 'en'. A message with no letters ("3", "2h") keeps the previous language."""
    lowered = text.lower().strip(" ?!.")
    if VI_LETTERS.search(lowered) or lowered in UNACCENTED_VI:
        return "vi"
    # ponytail: Vietnamese typed without accents reads as English, add a word list if users do that
    return "en" if re.search(r"[a-z]{2,}", lowered) else previous


def t(lang: str, key: str, **values) -> str:
    template = VI.get(key, EN.get(key, key)) if lang == "vi" else EN.get(key, key)
    return template.format(**values) if values else template


EN = {
    "help_text": (
        "I turn what you need to do into tasks and a proposed study schedule, keep your notes, and quiz you on them.\n"
        "- Plan: \"I have a calculus problem set due Friday and a midterm next Wednesday.\"\n"
        "- Study time: \"3 hours on weekdays, I'm busy on Saturday.\"\n"
        "- Update: \"Mark calculus problem set as done.\", \"Do the midterm after the problem set.\", \"Show my plan.\"\n"
        "- Notes: \"save note: Derivatives - the derivative of x^2 is 2x #calculus\", \"find notes about derivatives\", "
        "\"link note 1 to task 2\", \"delete note 1\".\n"
        "- Study: \"quiz me on derivatives\" or \"study note 1\", then answer the questions.\n"
        "- Campus offices: \"Where is the library?\"\n"
        "Type \"reset\" to start a new plan. Vietnamese works too."
    ),
    "fallback_text": (
        "I can't help with that yet. Tell me about tasks and deadlines, for example \"I have an essay due Friday\", "
        "save a note, or ask where a campus office is."
    ),
}

VI = {
    "help_text": (
        "Mình biến việc bạn cần làm thành danh sách việc và lịch học đề xuất, lưu ghi chú và hỏi bài từ ghi chú đó.\n"
        "- Lập kế hoạch: \"Tôi có bài tập giải tích hạn thứ 6 và thi giữa kỳ thứ 4 tuần sau.\"\n"
        "- Thời gian học: \"Mỗi ngày tôi học được 3 tiếng, thứ 7 bận.\"\n"
        "- Cập nhật: \"Đánh dấu bài tập giải tích là xong\", \"Ôn thi giữa kỳ sau khi xong bài tập giải tích\", \"Xem kế hoạch\".\n"
        "- Ghi chú: \"lưu ghi chú: Đạo hàm - đạo hàm của x^2 là 2x #giaitich\", \"tìm ghi chú về đạo hàm\", "
        "\"gắn ghi chú 1 với việc 2\", \"xóa ghi chú 1\".\n"
        "- Học tập: \"kiểm tra tôi về đạo hàm\" hoặc \"ôn ghi chú 1\", rồi trả lời các câu hỏi.\n"
        "- Phòng ban: \"Thư viện ở đâu?\"\n"
        "Gõ \"làm lại\" để bắt đầu kế hoạch mới. Tiếng Anh cũng được."
    ),
    "fallback_text": (
        "Mình chưa giúp được việc này. Hãy kể về việc cần làm và hạn chót, ví dụ \"Tôi có bài tiểu luận hạn thứ 6\", "
        "lưu một ghi chú, hoặc hỏi phòng ban ở đâu."
    ),
    # service: general
    "Please type a request.": "Vui lòng nhập yêu cầu.",
    "Hello! Tell me what you need to get done, save a note, or type \"help\".":
        "Xin chào! Hãy cho mình biết bạn cần làm gì, lưu một ghi chú, hoặc gõ \"giúp\".",
    "Your plan is cleared. Your saved notes are kept. What do you need to do?":
        "Đã xóa kế hoạch. Ghi chú của bạn vẫn được giữ. Bạn cần làm gì?",
    "You have no tasks yet. Tell me what you need to do and when it is due.":
        "Bạn chưa có việc nào. Hãy cho mình biết bạn cần làm gì và hạn khi nào.",
    "You have no tasks yet, so there is nothing to mark as done.": "Bạn chưa có việc nào nên chưa có gì để đánh dấu xong.",
    "I couldn't find that task in your plan.": "Mình không tìm thấy việc đó trong kế hoạch.",
    "Marked \"{title}\" as done. ": "Đã đánh dấu \"{title}\" là xong. ",
    "\"{task}\" will start after \"{dep}\" is finished. ": "\"{task}\" sẽ bắt đầu sau khi xong \"{dep}\". ",
    "Tasks were read by the {name} language model. Check them before relying on the plan.":
        "Các việc được mô hình ngôn ngữ {name} đọc ra. Hãy kiểm tra lại trước khi dùng kế hoạch.",
    "The AI service is unavailable ({error}). Only rule-based reading was used.":
        "Dịch vụ AI không hoạt động ({error}). Chỉ dùng quy tắc để đọc tin nhắn.",
    "Tell me the hours for each day, for example: \"2 hours on weekdays, 4 hours on Sunday\".":
        "Hãy cho mình số giờ từng ngày, ví dụ: \"2 tiếng ngày thường, 4 tiếng chủ nhật\".",
    "2 hours on weekdays, 4 hours on Sunday": "2 tiếng ngày thường, 4 tiếng chủ nhật",
    # service: planning
    "I noted your study time. Now tell me what you need to do and when it is due.":
        "Mình đã ghi nhận thời gian học. Giờ hãy cho mình biết bạn cần làm gì và hạn khi nào.",
    "{note}I found {count} task. One thing is missing before I can schedule anything: how many hours can you study each day?":
        "{note}Mình tìm thấy {count} việc. Còn thiếu một thông tin trước khi xếp lịch: mỗi ngày bạn học được mấy tiếng?",
    "{note}I found {count} tasks. One thing is missing before I can schedule anything: how many hours can you study each day?":
        "{note}Mình tìm thấy {count} việc. Còn thiếu một thông tin trước khi xếp lịch: mỗi ngày bạn học được mấy tiếng?",
    "2 hours": "2 tiếng", "3 hours": "3 tiếng", "It changes by day": "Mỗi ngày một khác",
    "No study time is planned on {days} because none was given.": "Không xếp giờ học vào {days} vì bạn chưa cho biết.",
    "Here is a draft schedule. Change anything that looks wrong before you add it to your plan.":
        "Đây là lịch nháp. Hãy sửa chỗ nào chưa đúng trước khi đưa vào kế hoạch.",
    "Show my plan": "Xem kế hoạch", "reset": "làm lại",
    "2 hours on {day}": "2 tiếng vào {day}", "{hours} hours per day": "{hours} tiếng mỗi ngày",
    "{title} takes about {hours}": "{title} mất khoảng {hours}",
    "{title} on {when}": "{title} vào {when}", "{title} due {when}": "{title} hạn {when}", " at {time}": " lúc {time}",
    "{hours} of study time on {days}": "{hours} học vào {days}", "Busy on {days}": "Bận vào {days}",
    "{task} comes after {dep}": "{task} làm sau {dep}",
    "every day": "mọi ngày", "weekdays": "ngày thường", "weekends": "cuối tuần",
    # parser
    "Read 'next {day}' as {date}.": "Hiểu 'next {day}' là {date}.",
    "Read {dm} as {date} (day/month).": "Hiểu {dm} là {date} (ngày/tháng).",
    "No date was given for the {time} deadline, so it is read as today.": "Hạn lúc {time} không có ngày nên được hiểu là hôm nay.",
    "marked as important": "được đánh dấu quan trọng", "marked as low priority": "được đánh dấu ưu tiên thấp",
    "no deadline given": "chưa có hạn", "due within 2 days": "hạn trong 2 ngày", "due within 5 days": "hạn trong 5 ngày",
    "due in {days} days": "còn {days} ngày đến hạn",
    # scheduler
    "{title} due": "Hạn nộp {title}",
    "These tasks depend on each other in a loop, so that order was ignored: {titles}.":
        "Các việc này phụ thuộc vòng tròn vào nhau nên thứ tự đó bị bỏ qua: {titles}.",
    "{task} is planned after {dep} because it depends on it.": "{task} được xếp sau {dep} vì phụ thuộc vào việc đó.",
    "{title} has no deadline, so it is planned within the next 7 days.": "{title} chưa có hạn nên được xếp trong 7 ngày tới.",
    "{title} was due {date}, so it can no longer be scheduled.": "{title} đã hết hạn {date} nên không xếp lịch được nữa.",
    "the end of the week": "cuối tuần này",
    "Not enough time for {title}: it needs about {need}, but only {placed} fit before {limit}.":
        "Không đủ thời gian cho {title}: cần khoảng {need} nhưng chỉ xếp được {placed} trước {limit}.",
    "Not enough time for {title}: it needs about {need}, but only {placed} fit before {limit}: that time is already used by {users}.":
        "Không đủ thời gian cho {title}: cần khoảng {need} nhưng chỉ xếp được {placed} trước {limit}: thời gian đó đã dành cho {users}.",
    "Not enough time for {title}: it needs about {need}, but only {placed} fit before {limit}: there is no study time on those days.":
        "Không đủ thời gian cho {title}: cần khoảng {need} nhưng chỉ xếp được {placed} trước {limit}: những ngày đó không có giờ học.",
    # offices
    "{name}: room {room}, open {hours}.": "{name}: phòng {room}, mở cửa {hours}.",
    "{name}: the room and opening hours are not published.": "{name}: chưa công bố phòng và giờ mở cửa.",
    "Several offices match. Which one do you mean?": "Có nhiều phòng ban khớp. Bạn muốn hỏi phòng nào?",
    # knowledge
    "Tell me what to save, for example: save note: Derivatives - the derivative of x^2 is 2x #calculus. A link needs an address starting with http:// or https://.":
        "Hãy cho mình nội dung cần lưu, ví dụ: lưu ghi chú: Đạo hàm - đạo hàm của x^2 là 2x #giaitich. Liên kết cần địa chỉ bắt đầu bằng http:// hoặc https://.",
    "Saved note #{id}: {title}.": "Đã lưu ghi chú #{id}: {title}.",
    "Show my notes": "Xem ghi chú", "quiz me on {topic}": "kiểm tra tôi về {topic}",
    "You have no saved notes yet.": "Bạn chưa lưu ghi chú nào.",
    "Your notes:": "Ghi chú của bạn:",
    "No saved note matches \"{query}\". I only search notes you saved, so I have no source for it.":
        "Không có ghi chú nào khớp \"{query}\". Mình chỉ tìm trong ghi chú bạn đã lưu nên không có nguồn cho nội dung này.",
    "Notes about \"{query}\":": "Ghi chú về \"{query}\":",
    "I couldn't find that note or task. Check the numbers with \"show my notes\" and \"show my plan\".":
        "Mình không tìm thấy ghi chú hoặc việc đó. Kiểm tra số thứ tự bằng \"xem ghi chú\" và \"xem kế hoạch\".",
    "Linked note #{note} to \"{task}\".": "Đã gắn ghi chú #{note} với \"{task}\".",
    "There is no note #{id}.": "Không có ghi chú #{id}.",
    "Deleted note #{id}.": "Đã xóa ghi chú #{id}.",
    "your note #{id}": "ghi chú #{id} của bạn", "Source: {source}": "Nguồn: {source}",
    # study
    "Question {n}/{total}: {question}": "Câu {n}/{total}: {question}",
    "skip": "bỏ qua", "stop": "dừng",
    "I have no material on \"{topic}\" yet. Save a note first, for example: save note: {topic} - what you learned.":
        "Mình chưa có tài liệu về \"{topic}\". Hãy lưu ghi chú trước, ví dụ: lưu ghi chú: {topic} - nội dung bạn đã học.",
    "That note is too short to make questions from. Add a few full sentences to it.":
        "Ghi chú quá ngắn để tạo câu hỏi. Hãy thêm vài câu đầy đủ.",
    "Summary: {text}": "Tóm tắt: {text}",
    "You got {score} right. I suggest reviewing {topic} on {date}. Add that review to your plan?":
        "Bạn đúng {score} câu. Mình gợi ý ôn lại {topic} vào {date}. Thêm việc ôn tập vào kế hoạch nhé?",
    "add review to plan": "thêm ôn tập vào kế hoạch",
    "Quiz stopped. You answered {done} of {total} questions.": "Đã dừng. Bạn trả lời {done}/{total} câu.",
    "Finish a quiz first, then I can add a review to your plan.": "Hãy làm xong một bài kiểm tra trước, rồi mình thêm việc ôn tập vào kế hoạch.",
    "Added \"{title}\" to your plan. ": "Đã thêm \"{title}\" vào kế hoạch. ",
    "Correct!": "Chính xác!",
    "Not quite. The answer is: {answer}.": "Chưa đúng. Đáp án là: {answer}.",
    "Review {topic}": "Ôn tập {topic}",
    "Questions were written by the {name} model from your notes.": "Câu hỏi do mô hình {name} viết từ ghi chú của bạn.",
    "You have no notes on this topic, so the {name} model wrote these questions from general knowledge. Check them against your course material.":
        "Bạn chưa có ghi chú về chủ đề này nên mô hình {name} viết câu hỏi từ kiến thức chung. Hãy đối chiếu với tài liệu môn học.",
}
