import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import repl from "node:repl";
import util from "node:util";
import { PassThrough } from "node:stream";

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as z from "zod/v4";

const server = new McpServer({
  name: "node_repl_linux",
  version: "0.1.0",
});

const runtimeState = {
  moduleDirs: new Set(),
  currentExecution: null,
  replServer: null,
};

const serverDir = path.dirname(new URL(import.meta.url).pathname);
const externalNodeModulesDir = path.join(serverDir, "node_modules");
process.chdir(serverDir);

function ensureDirectory(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function formatValue(value) {
  if (typeof value === "string") {
    return value;
  }

  return util.inspect(value, {
    depth: 4,
    colors: false,
    maxArrayLength: 50,
    maxStringLength: 2000,
    breakLength: 100,
  });
}

function createConsoleBridge(execution) {
  const writeLine = (...args) => {
    execution.consoleOutput.push(util.format(...args));
  };

  return {
    log: writeLine,
    info: writeLine,
    debug: writeLine,
    warn: writeLine,
    error: writeLine,
    dir: (value, options) => {
      execution.consoleOutput.push(util.inspect(value, options));
    },
    clear: () => {},
    trace: (...args) => {
      const message = util.format(...args);
      execution.consoleOutput.push(message);
    },
  };
}

function createNodeReplApi() {
  return {
    get cwd() {
      return process.cwd();
    },
    get homeDir() {
      return os.homedir();
    },
    get tmpDir() {
      return os.tmpdir();
    },
    get requestMeta() {
      return null;
    },
    write(text) {
      if (runtimeState.currentExecution) {
        runtimeState.currentExecution.writeOutput.push(String(text));
      }
      return text;
    },
    setResponseMeta(meta) {
      if (runtimeState.currentExecution) {
        runtimeState.currentExecution.responseMeta = {
          ...runtimeState.currentExecution.responseMeta,
          ...meta,
        };
      }
    },
    async emitImage() {
      throw new Error("emitImage is not supported by this Linux node_repl shim");
    },
  };
}

function createReplServer() {
  const input = new PassThrough();
  const output = new PassThrough();
  const replServer = repl.start({
    prompt: "",
    input,
    output,
    terminal: false,
    useGlobal: false,
    ignoreUndefined: false,
  });

  replServer.context.nodeRepl = createNodeReplApi();
  replServer.context.console = createConsoleBridge({
    consoleOutput: [],
    writeOutput: [],
    responseMeta: {},
  });
  replServer.context.global = replServer.context;
  replServer.context.globalThis = replServer.context;
  return replServer;
}

function ensureReplServer() {
  if (!runtimeState.replServer) {
    runtimeState.replServer = createReplServer();
  }

  return runtimeState.replServer;
}

function closeReplServer() {
  if (runtimeState.replServer) {
    runtimeState.replServer.close();
    runtimeState.replServer = null;
  }
}

function beginExecution() {
  const execution = {
    consoleOutput: [],
    writeOutput: [],
    responseMeta: {},
  };
  runtimeState.currentExecution = execution;

  const replServer = ensureReplServer();
  replServer.context.console = createConsoleBridge(execution);

  return execution;
}

function endExecution() {
  runtimeState.currentExecution = null;
}

function runInRepl(code, timeoutMs) {
  const replServer = ensureReplServer();

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Execution timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    replServer.eval(code, replServer.context, "node-repl-linux", (error, result) => {
      clearTimeout(timer);
      if (error) {
        reject(error);
        return;
      }
      resolve(result);
    });
  });
}

function symlinkPackageEntry(sourceEntry, targetEntry) {
  const parentDir = path.dirname(targetEntry);
  ensureDirectory(parentDir);

  if (fs.existsSync(targetEntry)) {
    return false;
  }

  const linkType = fs.statSync(sourceEntry).isDirectory() ? "dir" : "file";
  fs.symlinkSync(sourceEntry, targetEntry, linkType);
  return true;
}

function linkNodeModules(sourceDir) {
  ensureDirectory(externalNodeModulesDir);
  let linkedSomething = false;

  for (const entry of fs.readdirSync(sourceDir, { withFileTypes: true })) {
    const sourceEntry = path.join(sourceDir, entry.name);
    const targetEntry = path.join(externalNodeModulesDir, entry.name);

    if (entry.name.startsWith("@") && entry.isDirectory()) {
      ensureDirectory(targetEntry);
      for (const scopedEntry of fs.readdirSync(sourceEntry, { withFileTypes: true })) {
        const sourceScopedEntry = path.join(sourceEntry, scopedEntry.name);
        const targetScopedEntry = path.join(targetEntry, scopedEntry.name);
        linkedSomething = symlinkPackageEntry(sourceScopedEntry, targetScopedEntry) || linkedSomething;
      }
      continue;
    }

    linkedSomething = symlinkPackageEntry(sourceEntry, targetEntry) || linkedSomething;
  }

  return linkedSomething;
}

server.registerTool(
  "js",
  {
    description: "Run JavaScript in a persistent Node REPL with top-level await support.",
    inputSchema: {
      code: z.string().describe("JavaScript source to execute."),
      timeout_ms: z.number().int().positive().max(300000).optional().describe("Optional timeout in milliseconds."),
      title: z.string().optional().describe("Optional human-readable label for the execution."),
    },
  },
  async ({ code, timeout_ms }) => {
    const execution = beginExecution();

    try {
      const result = await runInRepl(code, timeout_ms ?? 30000);
      const parts = [];

      if (execution.consoleOutput.length > 0) {
        parts.push(execution.consoleOutput.join("\n"));
      }

      if (execution.writeOutput.length > 0) {
        parts.push(execution.writeOutput.join(""));
      }

      if (typeof result !== "undefined") {
        parts.push(formatValue(result));
      }

      const text = parts.length > 0 ? parts.join("\n") : "(no output)";
      return {
        content: [
          {
            type: "text",
            text,
          },
        ],
      };
    } finally {
      endExecution();
    }
  }
);

server.registerTool(
  "js_reset",
  {
    description: "Reset the persistent Node REPL state while keeping added node_modules directories.",
    inputSchema: {},
  },
  async () => {
    closeReplServer();
    ensureReplServer();
    return {
      content: [
        {
          type: "text",
          text: "Node REPL state reset",
        },
      ],
    };
  }
);

server.registerTool(
  "js_add_node_module_dir",
  {
    description: "Add an absolute node_modules directory to the REPL package resolution path.",
    inputSchema: {
      path: z.string().describe("Absolute path to a node_modules directory."),
    },
  },
  async ({ path: moduleDir }) => {
    if (!path.isAbsolute(moduleDir)) {
      throw new Error("path must be an absolute path");
    }

    if (!fs.existsSync(moduleDir) || !fs.statSync(moduleDir).isDirectory()) {
      throw new Error(`node_modules directory not found: ${moduleDir}`);
    }

    const alreadyAdded = runtimeState.moduleDirs.has(moduleDir);
    runtimeState.moduleDirs.add(moduleDir);
    const linkedSomething = linkNodeModules(moduleDir);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            added: !alreadyAdded,
            linked_new_entries: linkedSomething,
            path: moduleDir,
          }),
        },
      ],
    };
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
