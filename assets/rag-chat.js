
(() => {
  const style = document.createElement("style");
  style.textContent = `
    #rag-room-launcher {
      right: 31px;
      bottom: 94px;
      width: 44px;
      height: 44px;
      padding: 0;
      z-index: 10000;
      cursor: pointer;
      font: inherit;
    }
    #rag-room-launcher svg {
      width: 21px;
      height: 21px;
      flex: 0 0 21px;
    }
    #rag-room-panel {
      position: fixed;
      right: 24px;
      bottom: 150px;
      z-index: 10001;
      width: min(400px, calc(100vw - 32px));
      height: min(500px, calc(100dvh - 170px));
      min-height: 180px;
      min-width: 280px;
      max-width: calc(100vw - 16px);
      max-height: calc(100dvh - 16px);
      resize: both;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid #58749b;
      border-radius: 12px;
      background: #101e33;
      color: #fff;
      box-shadow: 0 12px 35px #0007;
      font-family: inherit;
    }
    #rag-room-panel[hidden] { display: none; }
    .rag-room-header, .rag-room-form {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
    }
    .rag-room-header {
      justify-content: space-between;
      border-bottom: 1px solid #344966;
      min-width: 280px;
      max-width: calc(100vw - 16px);
      max-height: calc(100dvh - 16px);
      resize: both;
    }
    .rag-room-header button {
      background: transparent;
      border: 0;
      color: #fff;
      cursor: pointer;
    }
    #rag-room-messages {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 14px;
      font-size: 14px;
      line-height: 1.6;
    }
    .rag-room-message {
      padding: 10px;
      margin-bottom: 12px;
      border-radius: 8px;
      background: #243752;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .rag-room-message.user { background: #355880; }
    .rag-room-evidence {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #58749b;
      color: #c4d5ed;
      font-size: 12px;
    }
    .rag-room-evidence a { color: #a9d2ff; }
    .rag-room-form { border-top: 1px solid #344966; }
    #rag-room-input {
      flex: 1;
      min-width: 0;
      padding: 10px;
      border: 1px solid #58749b;
      border-radius: 6px;
      background: #172b47;
      color: #fff;
      font: inherit;
    }
    .rag-room-form button {
      padding: 10px;
      border: 0;
      border-radius: 6px;
      background: #70edc8;
      color: #102133;
      cursor: pointer;
    }
    @media (max-width: 768px) {
      #rag-room-launcher {
        right: 21px;
        bottom: 80px;
        width: 42px;
        height: 42px;
      }
      #rag-room-panel {
        right: 16px;
        bottom: 134px;
        height: min(500px, calc(100dvh - 150px));
      }
    }
  `;
  document.head.appendChild(style);

  const launcher = document.createElement("button");
  launcher.id = "rag-room-launcher";
  launcher.className = "newsroom-fab";
  launcher.type = "button";
  launcher.setAttribute("aria-label", "AI 근거 검색");
  launcher.setAttribute("aria-controls", "rag-room-panel");
  launcher.setAttribute("aria-expanded", "false");
  launcher.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20 11.5a8.5 8.5 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 20l1-4.5a8.5 8.5 0 1 1 16-4z"/>
    </svg>
    <span class="newsroom-fab-label">AI 근거 검색</span>
  `;

  const panel = document.createElement("section");
  panel.id = "rag-room-panel";
  panel.hidden = true;
  panel.setAttribute("aria-label", "AI 근거 검색");
  panel.innerHTML = `
    <div class="rag-room-header">
      <strong>AI 근거 검색</strong>
      <button type="button" id="rag-room-close" aria-label="닫기">✕</button>
    </div>
    <div id="rag-room-messages" role="log" aria-live="polite"></div>
    <form id="rag-room-form" class="rag-room-form">
      <input id="rag-room-input" type="text"
        placeholder="placeholder="정확한 답변을 위해 연도·지역(시도/자치구)·통계 대상을 포함해 질문해 주세요."
        aria-label="질문" maxlength="2000" required>
      <button type="submit">전송</button>
    </form>
  `;

  document.body.append(launcher, panel);

  const close = panel.querySelector("#rag-room-close");
  const form = panel.querySelector("#rag-room-form");
  const input = panel.querySelector("#rag-room-input");
  const messages = panel.querySelector("#rag-room-messages");
  const submit = form.querySelector('button[type="submit"]');

  const header = panel.querySelector(".rag-room-header");
  const layoutKey = "trafficRagWindowLayout";
  let layoutRestored = false;

  function saveWindowLayout() {
    if (panel.hidden) return;
    const rect = panel.getBoundingClientRect();

    try {
      localStorage.setItem(layoutKey, JSON.stringify({
        x: rect.left,
        y: rect.top,
        width: rect.width,
        height: rect.height
      }));
    } catch (_) {
      // 브라우저 저장소를 사용할 수 없어도 창은 동작한다.
    }
  }

  function keepWindowVisible() {
    if (panel.hidden) return;

    const rect = panel.getBoundingClientRect();
    const margin = 8;

    const width = Math.min(rect.width, window.innerWidth - margin * 2);
    const height = Math.min(rect.height, window.innerHeight - margin * 2);

    panel.style.width = `${width}px`;
    panel.style.height = `${height}px`;
    panel.style.left = `${Math.max(margin, Math.min(
      rect.left, window.innerWidth - width - margin
    ))}px`;
    panel.style.top = `${Math.max(margin, Math.min(
      rect.top, window.innerHeight - height - margin
    ))}px`;

    panel.style.right = "auto";
    panel.style.bottom = "auto";
  }

  function restoreWindowLayout() {
    if (layoutRestored) return;
    layoutRestored = true;

    try {
      const saved = JSON.parse(localStorage.getItem(layoutKey) || "null");

      if (saved &&
          [saved.x, saved.y, saved.width, saved.height]
            .every(Number.isFinite)) {
        panel.style.width = `${saved.width}px`;
        panel.style.height = `${saved.height}px`;
        panel.style.left = `${saved.x}px`;
        panel.style.top = `${saved.y}px`;
        panel.style.right = "auto";
        panel.style.bottom = "auto";
      }
    } catch (_) {
      // 저장된 배치가 없으면 기본 위치를 사용한다.
    }

    keepWindowVisible();
  }

  header.addEventListener("pointerdown", event => {
    if (event.button !== 0 || event.target.closest("button")) return;

    const rect = panel.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    const offsetY = event.clientY - rect.top;

    panel.style.left = `${rect.left}px`;
    panel.style.top = `${rect.top}px`;
    panel.style.right = "auto";
    panel.style.bottom = "auto";

    header.setPointerCapture(event.pointerId);

    function move(event) {
      panel.style.left = `${Math.max(8, Math.min(
        event.clientX - offsetX,
        window.innerWidth - panel.offsetWidth - 8
      ))}px`;

      panel.style.top = `${Math.max(8, Math.min(
        event.clientY - offsetY,
        window.innerHeight - panel.offsetHeight - 8
      ))}px`;
    }

    function stop() {
      header.removeEventListener("pointermove", move);
      header.removeEventListener("pointerup", stop);
      header.removeEventListener("pointercancel", stop);
      keepWindowVisible();
      saveWindowLayout();
    }

    header.addEventListener("pointermove", move);
    header.addEventListener("pointerup", stop);
    header.addEventListener("pointercancel", stop);
  });

  const windowResizeObserver = new ResizeObserver(() => {
    if (!panel.hidden) saveWindowLayout();
  });
  windowResizeObserver.observe(panel);

  window.addEventListener("resize", () => {
    if (!panel.hidden) {
      keepWindowVisible();
      saveWindowLayout();
    }
  });


  
  function setOpen(open) {
    panel.hidden = !open;
    launcher.setAttribute("aria-expanded", String(open));

    if (open) {
      restoreWindowLayout();
      keepWindowVisible();
      input.focus();
    } else {
      launcher.focus();
    }
  }

  launcher.addEventListener("click", () => setOpen(panel.hidden));
  close.addEventListener("click", () => setOpen(false));

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !panel.hidden) setOpen(false);
  });

  function addMessage(content, type = "assistant") {
    const message = document.createElement("div");
    message.className = "rag-room-message " + type;
    message.textContent = content;
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
    return message;
  }

  let activeArticleId = null;
  let activeArticleEditable = false;

  document.addEventListener("newsroom:draft-selected", event => {
    activeArticleId = event.detail.articleId;
    activeArticleEditable = event.detail.editable;
  });

  async function attachEvidence(item, checked, statusElement, button) {
    if (!activeArticleId || !activeArticleEditable) {
      statusElement.textContent =
        "기사 초안 메뉴에서 검토대기 기사를 먼저 선택하세요.";
      return;
    }

    const articleId = activeArticleId;
    button.disabled = true;
    statusElement.textContent = "근거 저장 중…";

    try {
      const response = await fetch(
        `/api/newsroom/drafts/${articleId}/rag-evidence`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            evidence_id: item.id,
            original_checked: checked
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "근거 연결 실패");
      }

      statusElement.textContent =
        `기사 #${articleId}에 연결 완료 · ` +
        (data.verification_status === "VERIFIED"
          ? "원문 대조 확인"
          : "원문 확인 필요");

    } catch (error) {
      statusElement.textContent = `오류: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  }

  function addEvidence(message, evidence) {
    if (!Array.isArray(evidence) || !evidence.length) return;

    const details = document.createElement("details");
    details.className = "rag-room-evidence";

    const summary = document.createElement("summary");
    summary.textContent = `근거 ${evidence.length}개 보기`;
    details.appendChild(summary);

    for (const item of evidence) {
      const block = document.createElement("p");
      block.textContent = [
        item.id,
        item.title,
        item.excerpt || item.source_file
      ].filter(Boolean).join("\n");

      if (item.url) {
        try {
          const url = new URL(item.url, window.location.href);
          if (url.protocol === "https:" || url.protocol === "http:") {
            const link = document.createElement("a");
            link.href = url.href;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "원문 열기";
            block.append("\n", link);
          }
        } catch (_) {
          // 유효하지 않은 출처 URL은 링크로 표시하지 않음
        }
      }

      if (
        typeof item.id === "string" &&
        /^(LAW|RULE)-/.test(item.id)
      ) {
        const controls = document.createElement("div");
        controls.style.marginTop = "10px";

        const label = document.createElement("label");
        label.style.display = "block";
        label.style.marginBottom = "8px";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";

        label.append(
          checkbox,
          document.createTextNode(
            " 법제처 원문과 발췌문을 직접 대조했습니다"
          )
        );

        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "선택한 기사에 근거 연결";
        button.style.padding = "7px 10px";
        button.style.borderRadius = "6px";
        button.style.background = "#70edc8";
        button.style.color = "#102133";
        button.style.border = "0";
        button.style.cursor = "pointer";

        const result = document.createElement("p");
        result.setAttribute("role", "status");
        result.style.marginTop = "8px";

        button.addEventListener("click", () => {
          attachEvidence(item, checkbox.checked, result, button);
        });

        controls.append(label, button, result);
        block.appendChild(controls);
      }

      details.appendChild(block);
    }

    message.appendChild(details);
  }


  const historyKey = "trafficRagChatHistory";

  function readHistory() {
    try {
      return JSON.parse(sessionStorage.getItem(historyKey) || "[]");
    } catch {
      return [];
    }
  }

  
  
  function saveExchange(question, answer, evidence = [], resolvedQuestion = question) {
    try {
      const history = readHistory();
      history.push({ question, answer, evidence, resolvedQuestion });
      sessionStorage.setItem(
        historyKey,
        JSON.stringify(history.slice(-30))
      );
    } catch {
      // 저장에 실패해도 채팅은 계속 작동
    }
  }

  function restoreHistory() {
    const history = readHistory();
    if (!Array.isArray(history)) return;

    history.forEach(item => {
      if (!item || typeof item.question !== "string"
          || typeof item.answer !== "string") return;

      addMessage(item.question, "user");
      const reply = addMessage(item.answer);
      addEvidence(
        reply,
        Array.isArray(item.evidence) ? item.evidence : []
      );
    });
  }

  restoreHistory();

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const question = input.value.trim();
    if (!question || submit.disabled) return;

    addMessage(question, "user");
    input.value = "";
    submit.disabled = true;

    const reply = addMessage("근거를 검색하고 있습니다.");

    try {
      const response = await fetch("/api/rag/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },   
        body: JSON.stringify({
          question,
          history: readHistory()
            .filter(item =>
              item &&
              typeof item.question === "string" &&
              typeof item.answer === "string" &&
              !item.answer.startsWith("오류:") &&
              !item.answer.includes("근거만으로는") &&
              !item.answer.includes("근거를 찾지 못했습니다")
            )
            .slice(-3)
            .map(item => ({
              question: item.question,
              resolvedQuestion: item.resolvedQuestion || item.question
            }))
        })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "요청에 실패했습니다.");
      }

      reply.textContent = data.answer || "답변이 없습니다.";
      addEvidence(reply, data.evidence);
      saveExchange(
        question,
        data.answer || "답변이 없습니다.",
        data.evidence,
        data.resolved_question || question
      );

    } catch (error) {
      reply.textContent = "오류: " + error.message;
      saveExchange(question, reply.textContent);
    } finally {
      submit.disabled = false;
      input.focus();
      messages.scrollTop = messages.scrollHeight;
    }
  });
})();