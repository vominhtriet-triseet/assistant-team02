# Trình bày tiến độ dự án: câu hỏi, câu trả lời và minh chứng

Tài liệu này giúp nhóm chuẩn bị trả lời các câu hỏi của giảng viên về tiến độ. Mỗi câu trả lời phân biệt rõ nội dung hiện có trong repo với phần dự kiến phát triển. Các liên kết dẫn đến file có thể mở trực tiếp khi thuyết trình.

## Nguyên tắc trình bày

Khi đưa minh chứng, có thể nói:

> File này mô tả hành vi dự kiến, còn file code này cho thấy phần đã được triển khai hiện tại. Nhóm chỉ báo cáo một tính năng là hoàn thành khi tính năng đó có code, có test và có thể demo hoạt động.

Repo của nhóm:

- [GitHub repository](https://github.com/vominhtriet-triseet/assistant-team02)
- [README dự án](../README.md)
- [Audit và roadmap của repo](repository-audit-roadmap.md)

---

## 1. Dự án giải quyết vấn đề gì?

### Câu trả lời gợi ý

Dự án hướng tới hỗ trợ sinh viên tổ chức công việc và việc học. Trợ lý nhận yêu cầu tự nhiên và hỗ trợ chuyển yêu cầu đó thành task, mức ưu tiên, ràng buộc, lịch, mục kiến thức hoặc hoạt động học tập. Định hướng hiện tại gồm ba tính năng: Planning and task execution, Knowledge management và Study support.

### Minh chứng nên mở

- [Problem boundary](problem-boundary.md): người dùng mục tiêu, khó khăn, use case, ràng buộc và quá trình chuyển đổi chính.
- [UI flow](../ui/README.md): nhập yêu cầu tự nhiên, định tuyến, hỏi làm rõ, fallback và hiển thị kết quả.
- [README dự án](../README.md): mô tả dự án và hướng dẫn cài đặt hiện có.

### Link GitHub

- [Problem boundary trên GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/docs/problem-boundary.md)
- [UI flow trên GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/ui/README.md)

---

## 2. Nhóm đã hoàn thành những gì?

### Câu trả lời gợi ý

Repo hiện có prototype rule-based để phản hồi lời chào và tra cứu văn phòng, dữ liệu văn phòng và task mẫu tổng hợp, giao diện tĩnh mẫu cùng một số tài liệu yêu cầu ban đầu. Nhóm cũng đã rà soát repo và ghi lại các việc còn lại trong audit roadmap. Ba tính năng chính vẫn chưa hoàn thành.

### Minh chứng nên mở

- [Rule-based assistant](../assistant/rules.py): logic lời chào và tra cứu văn phòng.
- [CLI entry point](../assistant/__main__.py): cách chạy trợ lý hiện tại.
- [Dữ liệu văn phòng](../data/offices.csv): dữ liệu tra cứu hiện có.
- [Task mẫu](../data/sample_tasks.csv): dữ liệu task tổng hợp.
- [UI prototype](../ui/index.html): giao diện hiện tại.
- [Roadmap của repo](repository-audit-roadmap.md): trạng thái và các việc còn thiếu.

### Cách diễn đạt nên dùng

Nên nói **prototype** hoặc **bản triển khai ban đầu**, không nên nói “trợ lý hoàn chỉnh đã xong”.

---

## 3. Ba tính năng đã hoạt động chưa?

### Câu trả lời gợi ý

Chưa. Planning chưa có vòng đời task hoàn chỉnh hoặc scheduler. Knowledge management chưa có quy trình lưu và tìm kiếm ghi chú hoàn chỉnh. Study support chưa có quy trình luyện tập và theo dõi tiến độ hoàn chỉnh. UI cũng chưa kết nối với backend. Nhóm xem đây là các phần MVP sẽ triển khai tiếp; chỉ báo cáo hoàn thành khi có code, test và demo hoạt động.

### Minh chứng nên mở

- [Tóm tắt audit](repository-audit-roadmap.md): bảng hiện trạng triển khai.
- [UI placeholder](../ui/index.html): thể hiện backend chưa được kết nối.
- [Yêu cầu Planning](problem-boundary.md): mô tả hành vi dự kiến cần triển khai.
- [Phạm vi UI ban đầu](../ui/README.md): tương tác task, lịch và reschedule dự kiến.

### Link GitHub

- [UI placeholder trên GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/ui/index.html)
- [Audit roadmap trên GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/docs/repository-audit-roadmap.md)

---

## 4. Phần nào hiện có thể chạy được?

### Câu trả lời gợi ý

Phần đang có là trợ lý rule-based xử lý lời chào và tra cứu văn phòng. Class capability trong backend là một prototype riêng, chưa phải application service chính thức. Nhóm đang hợp nhất các phần này để CLI, UI, evaluator và API sau này dùng chung một service contract.

### Minh chứng nên mở

- [Rules hiện tại](../assistant/rules.py).
- [CLI hiện tại](../assistant/__main__.py).
- [Backend prototype](../backend/main.py).
- [Backend README](../backend/README.md): thể hiện một số điểm tài liệu hiện cần chỉnh lại.
- [Cấu hình đóng gói](../pyproject.toml): hiện đang giả định layout `src`.

---

## 5. Tại sao nhóm gộp Scheduling & Planning với Task & Project Management?

### Câu trả lời gợi ý

Hai phần này cùng thao tác trên đối tượng chính là task. Một task có tiêu đề, thời lượng, deadline, độ ưu tiên, trạng thái và có thể có dependency. Task management tạo và theo dõi công việc; scheduling sắp xếp công việc đó vào thời gian khả dụng. Gộp chúng thành Planning and task execution giúp tạo thành một vòng đời thống nhất thay vì tách hai phần liên quan chặt chẽ.

### Minh chứng nên mở

- [Problem boundary](problem-boundary.md): trích xuất task, ưu tiên, ràng buộc, lập lịch và điều chỉnh kế hoạch.
- [Dữ liệu task mẫu](../data/sample_tasks.csv): có thời lượng, deadline, importance và status.
- [UI flow](../ui/README.md): tạo task, lập lịch, cập nhật task và reschedule.

---

## 6. Ba tính năng kết nối với nhau như thế nào?

### Câu trả lời gợi ý

Planning chuyển mục tiêu thành task và lịch. Knowledge management lưu ghi chú, tài liệu và nguồn liên quan. Study support sử dụng những tài liệu đó để giải thích, luyện tập, phản hồi và đề xuất ôn tập. Ví dụ, sinh viên lưu tài liệu về một chủ đề, tạo buổi học từ tài liệu đó, làm bài luyện tập rồi đặt lịch ôn tiếp theo.

### Minh chứng nên mở

- [Problem boundary](problem-boundary.md): quy trình lập kế hoạch và điều chỉnh.
- [UI flow](../ui/README.md): quy trình task và schedule.
- [Thiết kế hiển thị nguồn](ui-sources.md): cách hiển thị nguồn cho thông tin được truy xuất.
- [Task mẫu](../data/sample_tasks.csv): dữ liệu tổng hợp có thể dùng cho demo lập lịch học.
- [Phần abstraction trong roadmap](repository-audit-roadmap.md): context và response contract dùng chung.

---

## 7. Nhóm áp dụng decomposition, pattern recognition và abstraction như thế nào?

### Câu trả lời gợi ý

Decomposition chia mỗi tính năng thành các thao tác nhỏ. Với Planning, quy trình gồm nhận yêu cầu, trích xuất task, đặt ưu tiên, kiểm tra ràng buộc, lập lịch và theo dõi tiến độ. Pattern recognition giúp nhận ra các luồng lặp lại như mục tiêu đến task đến thời gian thực hiện, ghi nhận đến sắp xếp đến tìm kiếm, hoặc giải thích đến làm thử đến nhận phản hồi rồi ôn tập. Abstraction tạo ra các cấu trúc ổn định như Task, KnowledgeItem, StudySession và response contract để code không phụ thuộc vào cách diễn đạt riêng của từng câu yêu cầu.

### Minh chứng nên mở

- [Audit roadmap](repository-audit-roadmap.md): decomposition, domain model và response contract.
- [Problem boundary](problem-boundary.md): quy trình task và scheduling dự kiến.
- [UI flow](../ui/README.md): pattern input, routing, clarification, fallback và result.
- [Quy tắc hiển thị nguồn](ui-sources.md): pattern hiển thị source.

### Lưu ý

Phân tích tư duy tính toán ban đầu nằm trong tài liệu thuyết trình của nhóm. Roadmap trong repo là bản kết nối các ý tưởng đó với công việc triển khai.

---

## 8. Nhóm sẽ triển khai Planning and task execution như thế nào?

### Câu trả lời gợi ý

Trước tiên, nhóm sẽ định nghĩa Task với mã định danh, tiêu đề, thời lượng, deadline, độ ưu tiên, trạng thái và dependency. MVP sẽ hỗ trợ tạo, cập nhật, hoàn thành, hoãn và reschedule task. Scheduler deterministic sẽ tạo lịch đề xuất, phát hiện xung đột và liệt kê task chưa xếp được. Nếu thiếu thông tin như thời lượng, deadline hoặc availability, trợ lý sẽ hỏi lại thay vì tự đoán.

### Minh chứng nên mở

- [Yêu cầu Planning](problem-boundary.md): use case và ràng buộc.
- [Yêu cầu hiển thị kết quả UI](../ui/README.md): lịch đề xuất, cảnh báo, task chưa được xếp và reschedule.
- [CSV task mẫu](../data/sample_tasks.csv): các trường dữ liệu ban đầu.
- [Kế hoạch Planning MVP](repository-audit-roadmap.md): phần Planning MVP.

---

## 9. Tại sao gọi kết quả là “lịch đề xuất”, không phải lịch được đảm bảo?

### Câu trả lời gợi ý

Kết quả phụ thuộc vào thông tin người dùng cung cấp. Nếu thiếu availability, thời lượng, dependency hoặc deadline bị xung đột thì hệ thống không thể khẳng định lịch chắc chắn khả thi hay tối ưu. Vì vậy, hệ thống sẽ hiển thị lịch đề xuất cùng giả định, cảnh báo, xung đột và task chưa được xếp để người dùng kiểm tra.

### Minh chứng nên mở

- [Ràng buộc trong problem boundary](problem-boundary.md): input thiếu, tính khả thi và uncertainty.
- [UI result behavior](../ui/README.md): phân biệt lịch đề xuất với lịch chắc chắn khả thi.
- [Audit roadmap](repository-audit-roadmap.md): ScheduleProposal, warnings, assumptions và task chưa được xếp.

---

## 10. Knowledge management sẽ hoạt động như thế nào?

### Câu trả lời gợi ý

Nhóm sẽ biểu diễn thông tin dưới dạng KnowledgeItem, gồm nội dung, tags, chủ đề và metadata nguồn. MVP hỗ trợ lưu và tìm kiếm ghi chú, truy xuất thông tin liên quan và trả citation khi có nguồn xác minh. Office lookup có thể là nguồn kiến thức đầu tiên, nhưng sẽ được đưa sau một knowledge interface có cấu trúc thay vì tồn tại như một rule trả chuỗi riêng lẻ.

### Minh chứng nên mở

- [Dữ liệu văn phòng](../data/offices.csv): dataset ban đầu có thể dùng như knowledge source.
- [Thiết kế hiển thị nguồn](ui-sources.md): quy tắc citation và không tự tạo nguồn.
- [Data README](../data/README.md): tài liệu dữ liệu hiện cần được cập nhật.
- [Kế hoạch Knowledge MVP](repository-audit-roadmap.md): model và search flow dự kiến.

### Cách diễn đạt cần chính xác

Nên nói “office lookup là prototype knowledge source ban đầu”, không nên nói “knowledge-management feature đã hoàn thành”.

---

## 11. Nhóm tránh tạo citation không có thật như thế nào?

### Câu trả lời gợi ý

Response chỉ chứa citation có cấu trúc khi nguồn thực sự có sẵn. UI sẽ render citation từ response contract, không tự trích hoặc bịa URL từ văn bản tự do. Nếu chưa có nguồn xác minh, hệ thống sẽ nói rõ là chưa có nguồn. Các URL ví dụ trong tài liệu thiết kế chỉ có mục đích minh họa.

### Minh chứng nên mở

- [Quy tắc nguồn](ui-sources.md): cấm tạo citation giả.
- [Dữ liệu văn phòng](../data/offices.csv): hiện còn thiếu metadata nguồn, đây là phần dự kiến cải thiện.
- [Knowledge roadmap](repository-audit-roadmap.md): model Source và Citation.

---

## 12. Study support sẽ hoạt động ra sao?

### Câu trả lời gợi ý

Study support sẽ bắt đầu từ mục tiêu học, chủ đề và buổi học. Trợ lý có thể giải thích khái niệm, đưa câu hỏi luyện tập, kiểm tra câu trả lời, phản hồi và đề xuất nội dung cần ôn. Buổi ôn tiếp theo có thể trở thành task trong Planning. Bản đầu sẽ dùng nội dung tổng hợp và rule deterministic trước khi cân nhắc dùng AI provider.

### Minh chứng nên mở

- [Ví dụ trong UI](../ui/index.html): ví dụ học tập hiện có và trạng thái placeholder.
- [Task mẫu](../data/sample_tasks.csv): có ví dụ task liên quan đến học tập.
- [Study roadmap](repository-audit-roadmap.md): model và luồng MVP của Study support.
- [Problem boundary](problem-boundary.md): quy tắc về uncertainty và dữ liệu tổng hợp.

---

## 13. UI đã kết nối với backend chưa?

### Câu trả lời gợi ý

Chưa. Trang HTML hiện tại là UI prototype. Form chưa gửi request thật mà chỉ thay đổi một dòng trạng thái trên trang. Sau khi response contract và application service ổn định, nhóm sẽ nối UI với service và bổ sung các trạng thái loading, hỏi làm rõ, thành công, xung đột, lỗi, citation và phản hồi học tập.

### Minh chứng nên mở

- [UI HTML](../ui/index.html): hành vi placeholder hiện tại.
- [UI README](../ui/README.md): flow routing và result dự kiến.
- [Kế hoạch tích hợp application](repository-audit-roadmap.md): canonical service và kết nối UI.

---

## 14. Nhóm đang kiểm thử dự án như thế nào?

### Câu trả lời gợi ý

Bộ test hiện tại cần được cải thiện. Một số smoke test chỉ là placeholder và luôn pass; test backend không nằm trong lần chạy pytest thông thường và không khớp với response hiện tại. Nhóm sẽ thay bằng behavior test gồm unit test, integration test, contract test và evaluation case. Khi có regression, test phải phát hiện và fail.

### Minh chứng nên mở

- [Smoke tests placeholder](../tests/test_smoke.py): các test luôn pass cần được thay thế.
- [Backend tests](../backend/test_help.py): test cũ, không khớp implementation.
- [Pytest configuration](../pyproject.toml): cấu hình discovery hiện tại.
- [Testing roadmap](repository-audit-roadmap.md): cấu trúc test và các trường hợp cần kiểm tra.

### Nếu được hỏi “hiện có bao nhiêu test pass?”

> Số lượng test pass hiện tại chưa phản ánh chất lượng đáng tin cậy vì một số test vẫn là placeholder. Nhóm đang thay bằng test kiểm tra hành vi thực tế, sau đó sẽ báo cáo theo feature và acceptance case.

---

## 15. Dự án hiện có sử dụng AI không?

### Câu trả lời gợi ý

Trợ lý có thể chạy hiện tại đang dùng rule-based logic. Trong code cũng ghi rõ AI chưa được bổ sung. Nhóm sẽ ổn định domain model, validation, response contract và evaluation trước. Nếu bổ sung AI sau này, AI sẽ được đặt sau một provider interface có thể thay thế; validation, cảnh báo, citation và privacy vẫn do application kiểm soát.

### Minh chứng nên mở

- [Rule-based assistant](../assistant/rules.py): implementation hiện tại.
- [AI analysis document](ai-or-not.md): tài liệu AI hiện cần được hoàn thiện.
- [Architecture roadmap](repository-audit-roadmap.md): kế hoạch tách provider và triển khai theo giai đoạn.

---

## 16. Nhóm bảo vệ quyền riêng tư dữ liệu như thế nào?

### Câu trả lời gợi ý

MVP sử dụng dữ liệu tổng hợp. Nhóm không đưa lịch cá nhân, danh sách task riêng tư, thông tin đăng nhập hay dữ liệu cá nhân của sinh viên vào repo. Hệ thống cũng cần tránh ghi log không cần thiết và phải hiển thị giả định thay vì âm thầm suy đoán hoặc thu thập thông tin cá nhân.

### Minh chứng nên mở

- [Problem boundary](problem-boundary.md): non-goals, privacy boundary, dữ liệu synthetic và constraints.
- [Quy tắc privacy và error UI](../ui/README.md): validation, credentials, logging và synthetic data.
- [Data documentation](../data/README.md): quy định dữ liệu cần khớp với file thực tế.

---

## 17. Rủi ro lớn nhất hiện nay là gì?

### Câu trả lời gợi ý

Rủi ro chính là các phần ứng dụng chưa kết nối với nhau, package layout chưa nhất quán, test tạo false-green, evaluator chưa hoạt động và tài liệu mô tả nhiều hơn code hiện có. Nhóm sẽ giảm rủi ro bằng cách thống nhất một application service, chia module theo feature, viết behavior test và duy trì bảng trạng thái capability.

### Minh chứng nên mở

- [Repository audit](repository-audit-roadmap.md): đánh giá rủi ro và thứ tự ưu tiên.
- [Packaging configuration](../pyproject.toml): điểm chưa khớp về `src` layout.
- [UI placeholder](../ui/index.html): tình trạng chưa tích hợp backend.
- [Evaluation runner](../eval/run.py): khoảng trống evaluator.
- [Smoke tests](../tests/test_smoke.py): test placeholder hiện tại.

---

## 18. Tiếp theo nhóm sẽ làm gì?

### Câu trả lời gợi ý

Công việc tiếp theo chia thành năm milestone:

1. Làm repo nhất quán và cài đặt được.
2. Triển khai Planning MVP.
3. Triển khai Knowledge MVP.
4. Triển khai Study MVP.
5. Tích hợp UI, evaluator và CI.

Luồng end-to-end đầu tiên nhóm hướng tới là:

```text
User request
→ canonical service
→ task, knowledge, hoặc study response
→ CLI hoặc UI
→ behavior test
→ evaluation result
```

### Minh chứng nên mở

- [Milestones trong audit roadmap](repository-audit-roadmap.md#suggested-milestones).
- [Thứ tự ưu tiên cuối cùng](repository-audit-roadmap.md#final-priority-order).
- [README dự án](../README.md): entry point và hướng dẫn hiện tại.

---

## 19. Công việc được chia cho sáu thành viên như thế nào?

### Câu trả lời gợi ý

Nhóm dự kiến chia ownership theo module để mọi người có thể làm độc lập:

| Username | Phạm vi phụ trách dự kiến |
|---|---|
| `vominhtriet-triseet` | Phạm vi sản phẩm, acceptance criteria, theo dõi tiến độ và tích hợp |
| `NPTho510` | Cấu trúc package, application service và response contract |
| `NiceBruhh` | Planning and task execution |
| `NguyenDuongAn` | Knowledge management và data catalog |
| `HaiTanh` | Study support, UI/UX và acceptance testing |
| `reiryuka` | CI, data validation và evaluator |

Mỗi người làm trên nhánh riêng và sở hữu module riêng. Những phần cần thống nhất chung được giới hạn ở response contract, quy tắc dữ liệu/timezone, lệnh test và quy trình branch.

### Minh chứng nên mở

- [Team roles](team.md): danh sách vai trò hiện có.
- [Repository roadmap](repository-audit-roadmap.md): module và milestone mục tiêu.
- [Team work plan](team-work-plan.md): phân công chi tiết và quy tắc bàn giao, nếu file này đã được thêm vào repo.

### Lưu ý cần xác nhận

[docs/team.md](team.md) hiện lặp `HaiTanh` ở hai vai trò QA và UI/UX, nên bảng vai trò chỉ có năm username khác nhau. `NiceBruhh` xuất hiện trong lịch sử contributor và đang được dùng tạm làm thành viên thứ sáu. Cần xác nhận username này với nhóm trước khi xem phân công là chính thức.

---

## 20. Khi nào một công việc được xem là hoàn thành?

### Câu trả lời gợi ý

Một task chỉ được xem là hoàn thành khi code nằm trong module được giao, behavior test bao gồm trường hợp bình thường và edge case, tài liệu được cập nhật, lệnh kiểm tra liên quan chạy thành công, và acceptance criteria được xác nhận trong pull request đã review. Chỉ tạo file hoặc viết mô tả thiết kế chưa được xem là hoàn thành.

### Minh chứng nên mở

- [Repository roadmap](repository-audit-roadmap.md): CI, governance và thứ tự ưu tiên.
- [Team work plan](team-work-plan.md): Definition of Done và quy tắc làm việc độc lập, nếu file này đã được thêm vào repo.

---

## Đoạn kết ngắn

> Nhóm đã có prototype ban đầu và đã rà soát lại yêu cầu, nhưng trợ lý đủ ba tính năng vẫn đang được phát triển. Mục tiêu trước mắt là làm repo nhất quán, có test đáng tin cậy, sau đó hoàn thành một Planning MVP. Tiếp theo nhóm sẽ phát triển Knowledge management và Study support trên cùng một application service và response contract. Nhóm chỉ báo cáo một tính năng là hoàn thành khi code, test, UI và tài liệu cùng phản ánh đúng hành vi đó.
