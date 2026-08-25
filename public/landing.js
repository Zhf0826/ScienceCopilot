// ScienceCopilot 教师版 Landing Page — 极简交互
(function () {
  // 快速开始表单：跳转到工作台并预填参数
  const qsForm = document.getElementById("quickstartForm");
  if (qsForm) {
    qsForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const grade = document.getElementById("qs-grade").value.trim();
      const topic = document.getElementById("qs-topic").value.trim();
      const goal = document.getElementById("qs-goal").value.trim();
      // 存储到 sessionStorage，工作台页面读取
      sessionStorage.setItem("qs-grade", grade);
      sessionStorage.setItem("qs-topic", topic);
      sessionStorage.setItem("qs-goal", goal);
      // 跳转到工作台
      window.location.href = "/app.html";
    });
  }

  // 导航高亮
  const sections = document.querySelectorAll("section[id]");
  const navLinks = document.querySelectorAll(".nav-link");

  window.addEventListener("scroll", () => {
    let current = "";
    sections.forEach((section) => {
      const sectionTop = section.offsetTop - 100;
      if (window.scrollY >= sectionTop) {
        current = section.getAttribute("id");
      }
    });
    navLinks.forEach((link) => {
      link.classList.toggle("active", link.getAttribute("href") === `#${current}`);
    });
  });

  // 平滑滚动
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
})();
