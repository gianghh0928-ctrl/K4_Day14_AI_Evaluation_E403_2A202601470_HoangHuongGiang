# Day 14 — Exercises

## AI Evaluation & Benchmarking · Lab Worksheet

**Thời gian làm bài:** 14:15–17:00

**Domain:** OrbitTech Store Customer Support

Điền trực tiếp câu trả lời vào file này. Golden dataset 20 QA được viết một lần
duy nhất trong `golden_dataset.json`, không chép lại toàn bộ vào Markdown.

---

Từ 14:15–14:30, cài môi trường và chạy baseline tests theo `guide_lab.md`.

---

## Part 1 — Warm-up (14:30–14:45)

### Exercise 1.1 — RAGAS Metric Thresholds

Theo bài giảng:

- 0.8–1.0: Good — monitor, maintain.
- 0.6–0.8: Needs work — analyze failures, iterate.
- Dưới 0.6: Significant issues — investigate.

Với từng metric, xác định khi nào score thấp có thể chấp nhận và khi nào là
critical.

| Metric | Acceptable Low Score Scenario | Critical Low Score Scenario | Action Required |
|---|---|---|---|
| Faithfulness | Trợ lý thêm lời chào lịch sự hoặc từ xã giao không có trong context nhưng thông tin chuyên môn hoàn toàn chính xác. | Trợ lý bịa đặt chính sách bảo hành, sai giá sản phẩm hoặc ngày hiệu lực (Hallucination nguy hiểm). | Thêm Grounding Guardrails trong system prompt; yêu cầu trích dẫn nguồn; hạ temperature về 0. |
| Answer Relevance | Khách hàng hỏi câu cực ngắn (vd: "đổi trả?"), trợ lý giải thích đầy đủ quy trình nên trùng lặp từ ngữ ít. | Trợ lý trả lời lạc đề, không đúng trọng tâm khách hàng hỏi (vd: hỏi bảo hành laptop lại trả lời cấu hình). | Cải thiện Query Rewriter/Intent Classifier; tinh chỉnh system prompt để tập trung vào intent chính. |
| Context Recall | Trợ lý chỉ lấy được thông tin cốt lõi để trả lời câu hỏi factual đơn giản mà bỏ qua thông tin phụ xung quanh. | Retriever bỏ sót hoàn toàn tài liệu/chunk chứa câu trả lời đúng (vd: thiếu quy định đổi trả hàng lỗi). | Tăng `top_k` retriever; cải thiện thuật toán tìm kiếm (Hybrid BM25 + Vector); điều chỉnh chunk size/overlap. |
| Context Precision | Chunk đúng nằm ở vị trí thứ 2 hoặc thứ 3 thay vì vị trí thứ 1 trong top_k, nhưng vẫn đủ thông tin cho generator. | Chunk liên quan bị đẩy xuống cuối (vị trí 4-5) trong khi các vị trí top 1-2 chứa toàn thông tin rác/nhiễu. | Triển khai Reranker (Cross-Encoder / overlap scoring); tối ưu hóa thuật toán xếp hạng retriever. |
| Completeness | Khách hàng hỏi 1 ý cụ thể và câu trả lời tập trung đúng ý đó, bỏ qua các điều kiện phụ không được hỏi tới. | Trả lời thiếu các bước quan trọng trong quy trình (vd: thiếu thông tin "cần mang theo hóa đơn mua hàng"). | Cập nhật Prompt Generation yêu cầu kiểm tra liệt kê đủ điều kiện; bổ sung thông tin từ retriever. |

### Exercise 1.2 — Bias trong LLM-as-a-Judge

Ba bias thường gặp:

- Position bias: judge ưu tiên answer xuất hiện trước.
- Verbosity bias: judge ưu tiên answer dài hơn.
- Self-preference: judge ưu tiên output giống chính model đó.

**Câu 1: Thiết kế experiment phát hiện position bias với ít nhất hai conditions.**

> *Câu trả lời:*
> - **Mục tiêu**: Kiểm tra xem LLM Judge có thiên vị đáp án đứng ở vị trí đầu tiên (Candidate A) hay không.
> - **Tập test**: Chọn 10-20 cặp câu trả lời (Answer 1 và Answer 2) cho cùng một câu hỏi từ hệ thống.
> - **Condition 1 (Original Order)**: Đưa vào prompt đánh giá với thứ tự: `Candidate A: Answer 1`, `Candidate B: Answer 2`.
> - **Condition 2 (Swapped Order)**: Tráo đổi vị trí: `Candidate A: Answer 2`, `Candidate B: Answer 1`.
> - **Đánh giá**: So sánh kết quả của 2 Condition. Nếu điểm của Answer 1 ở Condition 1 cao hơn hẳn khi nó trở thành Candidate B ở Condition 2 (chỉ vì vị trí xuất hiện), ta kết luận LLM Judge bị Position Bias.
> - **Khắc phục**: Chạy eval ở cả 2 vị trí và lấy điểm trung bình (Position Swapping / Pairwise Averaging).

**Câu 2: Làm thế nào giảm verbosity bias bằng rubric design?**

> *Câu trả lời:*
> 1. **Định nghĩa tiêu chí Mật độ thông tin (Information Density)**: Quy định điểm số dựa trên sự chính xác và súc tích, không phụ thuộc vào độ dài từ ngữ.
> 2. **Thiết lập quy tắc trừ điểm rào rào (Penalty Rule)**: Thêm câu lệnh rõ ràng trong Rubric: *"Nếu câu trả lời chứa thông tin thừa thãi, lặp từ, hoặc câu từ rườm rà không trực tiếp trả lời câu hỏi, trừ 1 điểm (tối đa đạt 4 điểm)"*.
> 3. **Cung cấp Few-shot Calibration Examples**: Đưa vào prompt các ví dụ mẫu (Few-shot): Ví dụ đáp án ngắn gọn nhưng đạt 5/5, và ví dụ đáp án rất dài nhưng bị 2/5 do rườm rà.

**Câu 3: Tại sao cần calibrate LLM judge với human labels?**

> *Câu trả lời:*
> 1. **Phát hiện Bias ẩn**: LLM Judge có thể mắc các lỗi hệ thống như Self-preference, Verbosity Bias, hoặc hiểu sai quy định riêng của OrbitTech Store.
> 2. **Đảm bảo tính tin cậy (Alignment)**: Đo lường độ tương quan (ví dụ: Cohen's Kappa hoặc Spearman Correlation) giữa điểm số LLM Judge và điểm số từ Chuyên gia Domain/Human Annotator.
> 3. **Cải tiến Rubric & Prompt**: Giúp tinh chỉnh lại Rubric và Prompt của Judge đến khi độ tương quan với con người đạt mức tin cậy (vd: >= 0.85) trước khi đưa vào tự động hóa hoàn toàn.

### Exercise 1.3 — Evaluation trong CI/CD

**Câu 1: Chọn threshold để block deployment.**

| Metric | Threshold | Lý do |
|---|---:|---|
| Faithfulness | **0.90 (90%)** | Bị đặt/sai thông tin (Hallucination) trong hỗ trợ khách hàng dễ dẫn đến khiếu nại, mất uy tín thương hiệu và thiệt hại tài chính. Đây là chỉ số quan trọng nhất không được thỏa hiệp. |
| Answer Relevance | **0.80 (80%)** | Đảm bảo câu trả lời trực tiếp giải quyết vấn đề của khách hàng, tránh trả lời lan man hoặc lạc đề gây lãng phí thời gian người dùng. |
| Completeness | **0.75 (75%)** | Đảm bảo cung cấp đủ thông tin và các bước hướng dẫn cần thiết cho khách hàng, tránh trả lời cộc lốc hoặc thiếu bước xử lý quan trọng. |

**Câu 2: Khi nào dùng offline evaluation, online evaluation và human review?**

> *Câu trả lời:*
> - **Offline Evaluation (Đánh giá ngoại tuyến)**:
>   * *Khi nào dùng*: Sử dụng trong quá trình phát triển (Development), trước mỗi đợt Release, khi thay đổi Prompt, cập nhật Model hoặc sửa đổi Retrieval Pipeline.
>   * *Đặc điểm*: Chạy tự động trên Golden Dataset 20–100+ câu hỏi bằng pytest/RAGAS để làm Quality Gate trong CI/CD Pipeline.
> - **Online Evaluation (Đánh giá trực tuyến)**:
>   * *Khi nào dùng*: Sử dụng liên tục trên môi trường Production với dữ liệu chat thực tế của người dùng (Real User Traffic).
>   * *Đặc điểm*: Theo dõi các thông số thời gian thực (latency, user thumbs up/down, implicit feedback) hoặc sample 5-10% traffic cho LLM Judge đánh giá để phát hiện Data Drift và sự cố tức thì.
> - **Human Review (Đánh giá bởi con người)**:
>   * *Khi nào dùng*: Thực hiện định kỳ (hàng tuần/tháng), khi cần Calibrate (hiệu chỉnh) LLM Judge, hoặc kiểm tra các ca lỗi nghiêm trọng (Incident analysis, Edge cases khó).
>   * *Đặc điểm*: Do chuyên gia/Annotator chấm tay dựa trên Rubric để đảm bảo tính chính xác cao nhất và bổ sung mẫu mới vào Golden Dataset.

---
- `evaluate_context_recall(contexts, expected)`
- `evaluate_context_precision(contexts, expected)`

Full pipeline:

- `run_full_eval(..., contexts=None)` luôn tính ba answer metrics.
- Nếu có `contexts`, tính và lưu thêm Context Recall và Context Precision.
- Retrieval scores không làm thay đổi `overall_score()` và pass rule gốc.

### Task 3 — LLMJudge

- `score_response(question, answer, rubric)`
- `detect_bias(scores_batch)`

### Task 4 — BenchmarkRunner

- `run(qa_pairs, agent_fn, evaluator)`
- `generate_report(results)`
- `run_regression(new_results, baseline_results)`
- `identify_failures(results, threshold)`

`BenchmarkRunner.run()` phải truyền `pair.retrieved_contexts` vào
`run_full_eval()`. Report phải có average của hai retrieval metrics.

### Task 5 — FailureAnalyzer

- `categorize_failures(failures)`
- `find_root_cause(failure)`
- `generate_improvement_suggestions(failures)`
- `generate_improvement_log(failures, suggestions)`

Kiểm tra:

```bash
pytest tests/ -v
```

`rerank_by_overlap()` là TODO bonus của Exercise 3.5. Test tương ứng được skip
nếu bạn chưa làm bonus.

---

## Part 3 — Golden Dataset & Real Benchmark (15:40–16:35)

### Exercise 3.1 — Build the Golden Dataset

Thiết kế và validate dataset theo Mục 5–6 trong `guide_lab.md`. Nội dung 20 QA
được điền trực tiếp trong `golden_dataset.json`; phần dưới chỉ ghi lại kết quả
và quyết định thiết kế, không chép lại toàn bộ QA.

**Kết quả dataset**

| Hạng mục | Kết quả |
|---|---|
| Tổng số records | ____ / 20 |
| Easy | ____ / 5 |
| Medium | ____ / 7 |
| Hard | ____ / 5 |
| Adversarial | ____ / 3 |
| Source documents được sử dụng | ____ / 10 |
| Validator status | PASS / FAIL |

**Ba case đại diện cho quyết định thiết kế**

| ID | Difficulty | Source document(s) | Vì sao case phù hợp với difficulty/attack type? |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

**Điểm khó nhất khi xây dựng expected answer hoặc evidence là gì?**

> *Câu trả lời:*

**Xác nhận:**

- [ ] Mọi claim trong expected answer đều có evidence hỗ trợ.
- [ ] Không có questions trùng ý và không dùng kiến thức ngoài corpus.
- [ ] `python validate_golden_dataset.py` báo `PASS`.

### Exercise 3.2 — Benchmark Run

Chạy:

```bash
python domain_assistant.py
python evaluate_answers.py
```

Copy bảng terminal vào đây hoặc điền từ `artifacts/benchmark_results.json`.

| ID | Question (short) | Ctx Recall | Ctx Precision | Faithfulness | Relevance | Completeness | Overall | Passed? | Failure Type |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| E01 | | | | | | | | | |
| E02 | | | | | | | | | |
| E03 | | | | | | | | | |
| E04 | | | | | | | | | |
| E05 | | | | | | | | | |
| M01 | | | | | | | | | |
| M02 | | | | | | | | | |
| M03 | | | | | | | | | |
| M04 | | | | | | | | | |
| M05 | | | | | | | | | |
| M06 | | | | | | | | | |
| M07 | | | | | | | | | |
| H01 | | | | | | | | | |
| H02 | | | | | | | | | |
| H03 | | | | | | | | | |
| H04 | | | | | | | | | |
| H05 | | | | | | | | | |
| A01 | | | | | | | | | |
| A02 | | | | | | | | | |
| A03 | | | | | | | | | |

**Aggregate Report**

- Overall pass rate: ____%
- Avg Context Recall: ____
- Avg Context Precision: ____
- Avg Faithfulness: ____
- Avg Relevance: ____
- Avg Completeness: ____
- Failure type distribution: ____

**Ba cases có Overall Score thấp nhất**

1. ID: ____ | Score: ____ | Failure type: ____
2. ID: ____ | Score: ____ | Failure type: ____
3. ID: ____ | Score: ____ | Failure type: ____

**Nhận xét ngắn:** Metric nào yếu nhất? Kết quả gợi ý vấn đề nằm ở retrieval
hay generation?

> *Câu trả lời:*

### Exercise 3.3 — LLM-as-a-Judge Rubric Design

Thiết kế rubric domain-specific cho OrbitTech Customer Support. Mỗi mức phải
đủ cụ thể để hai người chấm độc lập có thể hiểu giống nhau.

Chọn 3–5 dimensions:

- [ ] Correctness
- [ ] Completeness
- [ ] Relevance
- [ ] Evidence/citation
- [ ] Actionability
- [ ] Safety/privacy
- [ ] Tone/clarity
- [ ] Dimension khác: __________

| Score | Tiêu chí domain-specific | Ví dụ response |
|---:|---|---|
| 5 | | |
| 4 | | |
| 3 | | |
| 2 | | |
| 1 | | |

**Ba edge cases khó chấm**

| Edge Case | Tại sao khó chấm? | Rubric xử lý thế nào? |
|---|---|---|
| | | |
| | | |
| | | |

**Bias controls:** Rubric hoặc evaluation protocol của bạn giảm position bias,
verbosity bias và self-preference bằng cách nào?

> *Câu trả lời:*

### Exercise 3.4 — Framework Comparison (Bonus +10)

Chỉ làm sau khi hoàn thành 3.1–3.3. Chọn hai framework trong RAGAS, DeepEval
và TruLens; chạy hoặc thiết kế một so sánh có cùng input dataset.

| Tiêu chí | Framework 1: ____ | Framework 2: ____ |
|---|---|---|
| Setup complexity | | |
| Metrics available | | |
| CI/CD integration | | |
| Kết quả trên cùng dataset | | |
| Insight rút ra | | |

- Scores có nhất quán không?
- Framework nào strict hơn và vì sao?
- Hai framework có tìm ra cùng failure cases không?

> *Phân tích:*

### Exercise 3.5 — Retrieval Reranking (Bonus +5)

Mục tiêu: kiểm tra việc đổi thứ tự chunks có tăng Context Precision mà không
thay đổi Context Recall hay không.

1. Chọn ít nhất 5 cases từ `artifacts/actual_answers.json`.
2. Tính Context Recall và Context Precision trước rerank.
3. Implement `rerank_by_overlap()` hoặc một reranker khác.
4. Rerank cùng tập chunks, không thêm hoặc xóa chunk.
5. Tính lại hai metrics và giải thích kết quả.

| ID | Recall before | Recall after | Precision before | Precision after | Delta Precision |
|---|---:|---:|---:|---:|---:|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| **Avg** | | | | | |

**Tại sao Recall dự kiến không đổi?**

> *Câu trả lời:*

**Khi nào reranking không đủ và cần sửa retriever/query/chunking?**

> *Câu trả lời:*

---

## Part 4 — Reflection (16:35–16:50)

Hoàn thành `reflection.md` bằng kết quả thật từ Exercise 3.2.

---

## Completion Checklist

Hoàn thành kiểm tra cuối trong khoảng 16:50–17:00.

- [ ] Tất cả required tests pass.
- [ ] `golden_dataset.json` validate thành công.
- [ ] Exercise 3.1 hoàn thành trong file JSON và bảng kết quả phía trên.
- [ ] Exercise 3.2 có năm metrics, aggregate report và ba cases thấp nhất.
- [ ] Exercise 3.3 có rubric 1–5 và bias controls.
- [ ] `reflection.md` có ba failure analyses và regression strategy.
- [ ] Đã copy `template.py` thành `solution/solution.py`.
- [ ] Exercise 3.4 và 3.5 chỉ làm nếu chọn bonus.
