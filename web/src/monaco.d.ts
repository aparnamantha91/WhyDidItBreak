declare module "monaco-editor/editor/editor.api" {
  export * from "monaco-editor";
}
declare module "monaco-editor/languages/definitions/python/register";
declare module "*?worker" {
  const WorkerCtor: { new (): Worker };
  export default WorkerCtor;
}
