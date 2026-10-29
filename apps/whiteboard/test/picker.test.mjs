import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseHTML } from "linkedom";
import { createBoardPicker } from "../src/picker.js";

const { document } = parseHTML("<!doctype html><html><body></body></html>");
globalThis.document = document;
// linkedom does not implement text selection.
document.defaultView.HTMLInputElement.prototype.select ??= () => {};

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

function fakeStore(boards) {
  const calls = [];
  return {
    calls,
    async list() { calls.push(["list"]); return boards; },
    async create(title) { calls.push(["create", title]); return { id: "new-board-abcd", title }; },
    async rename(id, title) { calls.push(["rename", id, title]); return { id, title }; },
    async archive(id) { calls.push(["archive", id]); return { id, archived: true }; },
  };
}

function setup(boards = [{ id: "other", title: "Other" }]) {
  const store = fakeStore(boards);
  const opened = [];
  const archived = [];
  const picker = createBoardPicker({
    store,
    boardId: "default",
    openBoard: (id) => opened.push(id),
    onArchived: (id) => archived.push(id),
  });
  picker.setTitle("Default");
  document.body.append(picker.element);
  const $ = (selector) => picker.element.querySelector(selector);
  const $$ = (selector) => [...picker.element.querySelectorAll(selector)];
  const submit = (form) => form.dispatchEvent(new document.defaultView.Event("submit", { cancelable: true }));
  return { store, opened, archived, picker, $, $$, submit };
}

describe("board picker", () => {
  it("lists boards, marks the open one and switches on click", async () => {
    const { $, $$, opened, picker } = setup();
    const trigger = $(".whiteboard-picker__trigger");
    assert.equal(trigger.textContent.includes("Default"), true);
    trigger.click();
    assert.equal(trigger.getAttribute("aria-expanded"), "true");
    await settle();
    const items = $$(".whiteboard-picker__item");
    // The open board is listed even though it has not been saved yet.
    assert.deepEqual(items.map((item) => item.textContent), ["Default", "Other"]);
    assert.equal(items[0].getAttribute("aria-current"), "page");
    items[0].click();
    assert.deepEqual(opened, []);
    trigger.click();
    await settle();
    $$(".whiteboard-picker__item")[1].click();
    assert.deepEqual(opened, ["other"]);
    assert.equal($(".whiteboard-picker__panel").hidden, true);
    picker.dispose();
  });

  it("creates a board and opens it", async () => {
    const { $, store, opened, submit, picker } = setup();
    $(".whiteboard-picker__trigger").click();
    $(".whiteboard-picker__input").value = "Sprint plan";
    submit($(".whiteboard-picker__form"));
    await settle();
    assert.deepEqual(store.calls.at(-1), ["create", "Sprint plan"]);
    assert.deepEqual(opened, ["new-board-abcd"]);
    picker.dispose();
  });

  it("renames the open board and updates its title", async () => {
    const { $, $$, store, submit, picker } = setup();
    $(".whiteboard-picker__trigger").click();
    $$(".whiteboard-picker__link").find((b) => b.textContent === "Rename board").click();
    const input = $(".whiteboard-picker__actions .whiteboard-picker__input");
    assert.equal(input.value, "Default");
    input.value = "Ideas";
    submit($(".whiteboard-picker__actions form"));
    await settle();
    assert.deepEqual(store.calls.find((call) => call[0] === "rename"), ["rename", "default", "Ideas"]);
    assert.match($(".whiteboard-picker__trigger").textContent, /Ideas/);
    picker.dispose();
  });

  it("archives the open board only after confirmation", async () => {
    const { $, $$, store, archived, picker } = setup();
    $(".whiteboard-picker__trigger").click();
    $$(".whiteboard-picker__link").find((b) => b.textContent === "Archive board").click();
    assert.ok(!store.calls.some((call) => call[0] === "archive"));
    $(".whiteboard-picker__button--danger").click();
    await settle();
    assert.deepEqual(archived, ["default"]);
    picker.dispose();
  });

  it("shows store errors inside the panel", async () => {
    const { $, store, submit, picker } = setup();
    store.create = async () => { throw new Error("disk full"); };
    $(".whiteboard-picker__trigger").click();
    $(".whiteboard-picker__input").value = "X";
    submit($(".whiteboard-picker__form"));
    await settle();
    assert.match($('[role="alert"]').textContent, /disk full/);
    picker.dispose();
  });

  it("closes on outside pointerdown and removes its listener on dispose", async () => {
    const { $, picker } = setup();
    $(".whiteboard-picker__trigger").click();
    document.body.dispatchEvent(new document.defaultView.Event("pointerdown", { bubbles: true }));
    assert.equal($(".whiteboard-picker__panel").hidden, true);
    $(".whiteboard-picker__trigger").click();
    picker.dispose();
    assert.equal(picker.element.isConnected, false);
  });
});
