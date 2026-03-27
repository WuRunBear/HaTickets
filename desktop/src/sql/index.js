import Database from "tauri-plugin-sql-api";
import { appConfigDir } from "@tauri-apps/api/path";

// sql文件名
export const dbName = import.meta.env.DEV ? `sql-test.db` : `sql.db`;
let db;
// 日志表名称
// 根据 appid，动态更改
export let logTableName = "LOG";
// 全局setting表名称
export const settingTableName = "SETTINGS";

// Allowed table names to prevent SQL injection
const ALLOWED_TABLES = new Set([settingTableName]);

function isAllowedTable(name) {
    return ALLOWED_TABLES.has(name) || name === logTableName;
}

// Validate column names: only allow alphanumeric and underscores
function isValidColumnName(name) {
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

// 获取 appid
export const getAppId = async () => {
    const res = await selectAll(settingTableName);
    if(Array.isArray(res) && res.length) {
        return res[0].appid
    }

    return ''
}

// 修改log 表名
// 表名通过数据库中取
export const changeLogTableName = async () => {
    await initDb();
    // 设置唯一表名
    const appId = await getAppId()
    if(appId) {
        // Validate appId format before using in table name
        if (/^[a-zA-Z0-9_]+$/.test(appId)) {
            logTableName = `${appId}_LOG`;
        }
    }
};

export const dbPath = async () => {
    return `sqlite:${await appConfigDir()}${dbName}`
}

// 初始化数据库
export const initDb = async () => {
    if (db) return;
    db = await Database.load(await dbPath());
};

// 初始化 日志表
export const initLogTable = async () => {
    await initDb();
    await db.execute(
        `CREATE TABLE IF NOT EXISTS ${logTableName} (id INTEGER PRIMARY KEY AUTOINCREMENT, time TIMESTAMP NOT NULL, type TEXT, status INTEGER, title TEXT, msg TEXT);`
    );
    // Add index on time for query performance
    await db.execute(
        `CREATE INDEX IF NOT EXISTS idx_${logTableName}_time ON ${logTableName} (time);`
    );
};

// 初始化 设置表
export const initSettingTable = async () => {
    await initDb();
    await db.execute(
        `CREATE TABLE IF NOT EXISTS ${settingTableName} (proxy TEXT, appid_list TEXT, appid TEXT NOT NULL)`
    );
};

// 添加逻辑 - parameterized queries
export const insert = async (tableName, params) => {
    if (!isAllowedTable(tableName)) {
        throw new Error(`Table "${tableName}" is not allowed`);
    }

    const keys = Object.keys(params);
    if (keys.some(k => !isValidColumnName(k))) {
        throw new Error("Invalid column name detected");
    }

    const placeholders = keys.map(() => "?").join(", ");
    const values = keys.map(k => {
        const v = params[k];
        return typeof v === "object" ? JSON.stringify(v) : v;
    });

    return await db.execute(
        `INSERT INTO ${tableName} (${keys.join(", ")}) VALUES (${placeholders})`,
        values
    );
};

// !!!默认更新所有 - parameterized queries
export const update = async (tableName, params) => {
    if (!isAllowedTable(tableName)) {
        throw new Error(`Table "${tableName}" is not allowed`);
    }

    const keys = Object.keys(params);
    if (keys.some(k => !isValidColumnName(k))) {
        throw new Error("Invalid column name detected");
    }

    const setClauses = keys.map(k => `${k} = ?`).join(", ");
    const values = keys.map(k => {
        const v = params[k];
        return typeof v === "object" ? JSON.stringify(v) : v;
    });

    return await db.execute(
        `UPDATE ${tableName} SET ${setClauses}`,
        values
    );
};

export const execute = async (query, params = []) => {
    return await db.execute(query, params);
};

// 获取指定 - parameterized queries
export const select = async (query, params = []) => {
    return await db.select(query, params);
};

// 获取所有
export const selectAll = async (tableName) => {
    if (!isAllowedTable(tableName)) {
        throw new Error(`Table "${tableName}" is not allowed`);
    }
    return select(`SELECT * FROM ${tableName}`);
};
