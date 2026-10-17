
# UI Design: Sources Under Each Answer

## Goal

Show the sources supporting each assistant answer directly below that
answer. Users should be able to distinguish sourced information from
the assistant's explanation and open a source to verify the information.

## Design rules

- Display a "Sources" section directly below the answer it supports.
- Use numbered references such as [1] and [2] in the answer when practical.
- Show each source's title, publisher or website, and a clickable URL.
- Display multiple sources as a short list rather than one long paragraph.
- Only show sources actually used to produce the answer.
- If no sources are available, do not invent any. Display "No sources
  available for this answer."
- Keep sources associated with their own answer, especially when a chat
  contains multiple question-and-answer pairs.

## Example 1: One source

**Student asks**

Where is the university library?

**Assistant answer**

The library is in room B.201 and is open Monday to Saturday,
07:00–20:00. [1]

**Sources**

[1] Library location and opening hours  
Publisher: University office directory  
URL: `https://example.edu/offices/library`

**UI notes**

- Place the Sources section immediately below this answer.
- Make the source title clickable.
- Keep the reference number [1] consistent between the answer and source.
- The example URL is illustrative, not a verified university link.

---

## Example 2: Multiple sources

**Student asks**

How should I plan my revision before an exam?

**Assistant answer**

Start by distributing revision sessions across the days before the exam.
Use practice questions to identify weak areas, then spend more time on
those areas. [1][2]

**Sources**

[1] Spaced practice: learning and revision guidance  
Publisher: Learning resource  
URL: `https://example.org/spaced-practice`

[2] Practice testing and retrieval practice  
Publisher: Study skills resource  
URL: `https://example.org/practice-testing`

**UI notes**

- Show both sources as separate items under the same answer.
- Preserve the reference order used in the answer.
- Allow users to open each source independently.
- These example titles and URLs are illustrative, not verified references.

---

## Layout mockup

```text
Student: Where is the university library?

Assistant:
The library is in room B.201 and is open Monday to Saturday,
07:00–20:00. [1]

Sources
[1] Library location and opening hours
    University office directory · Open source ↗

----------------------------------------

Student: How should I plan my revision?

Assistant:
Distribute revision sessions and use practice questions
to identify weak areas. [1][2]

Sources
[1] Spaced practice · Open source ↗
[2] Practice testing · Open source ↗
```

## Future implementation

The UI should render sources from structured backend response data rather
than extracting URLs from arbitrary answer text.

A future source object may contain:
- `title`: source title
- `url`: destination URL
- `publisher`: publisher or website name

The final response schema must be agreed with the backend team before
implementation. The UI must not fabricate citations or imply that an
unverified source supports an answer.

## Acceptance checklist

- [x] Document the citation display design.
- [x] Include an example with one source.
- [x] Include an example with multiple sources.
- [x] Explain source placement, links, and reference numbering.
- [ ] Review against the team Definition of Done.
