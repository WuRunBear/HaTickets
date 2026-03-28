import { BAXIA_VERSIONED_URL, BAXIA_ENTRY_URL, BAXIA_INIT_DELAY_MS, BAXIA_CHECK_API_PATHS } from "./dm-config.js";

// 加载必要的生成 ua token 脚本
// Returns a Promise that resolves when both scripts load, or rejects on error/timeout
export function loadBaxiaScript() {
    const TIMEOUT_MS = 5000;

    return new Promise((resolve, reject) => {
        let loaded = 0;
        const totalScripts = 2;
        const timer = setTimeout(() => {
            reject(new Error("Baxia scripts load timeout after " + TIMEOUT_MS + "ms"));
        }, TIMEOUT_MS);

        function onScriptLoad() {
            loaded++;
            if (loaded >= totalScripts) {
                clearTimeout(timer);
                resolve();
            }
        }

        function onScriptError(e) {
            clearTimeout(timer);
            reject(new Error("Failed to load Baxia script: " + (e.target && e.target.src)));
        }

        const awscScript = document.createElement("script");
        awscScript.type = "text/javascript";
        awscScript.crossOrigin = "anonymous";
        awscScript.src = BAXIA_ENTRY_URL;
        awscScript.onload = onScriptLoad;
        awscScript.onerror = onScriptError;
        document.body.appendChild(awscScript);

        const baxiaCommonScript = document.createElement("script");
        baxiaCommonScript.type = "text/javascript";
        baxiaCommonScript.crossOrigin = "anonymous";
        baxiaCommonScript.src = BAXIA_VERSIONED_URL;
        baxiaCommonScript.onload = onScriptLoad;
        baxiaCommonScript.onerror = onScriptError;
        document.body.appendChild(baxiaCommonScript);
    });
}

// 初始化大麦baxia脚本
export function initBaxia() {
    if (window.baxiaCommon) {
        try {
            window.baxiaCommon.init({
                checkApiPath: function (i) {
                    return BAXIA_CHECK_API_PATHS.some(function (path) {
                        return -1 < i.indexOf(path);
                    });
                },
            });
        } catch (e) {
            console.error("初始化 baxia 失败", e);
            return false;
        }

        return true;
    }

    return false;
}

// 接口 form data 必要的参数
// 生成的值只能使用**两次**
export function getHeaderUaAndUmidtoken() {
    if (window.__baxia__ && window.__baxia__.getFYModule) {
        // "bx-ua"
        // "bx-umidtoken"
        return [
            window.__baxia__.getFYModule.getFYToken(),
            window.__baxia__.getFYModule.getUidToken(),
        ];
    }

    return [];
}

// 初始化时间
export const loadBaxiaTime = BAXIA_INIT_DELAY_MS;
