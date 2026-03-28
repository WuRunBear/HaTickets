import { Message } from "@arco-design/web-vue";
import {
    DM_TOKEN_COOKIE_KEY,
    ORDER_TAG_LIST,
    ORDER_HIERARCHY_LIST,
    DM_SUB_CHANNEL,
    MSG_TOKEN_EXPIRED,
} from "./dm-config.js";

export function getToken(cookie) {
    const list = cookie.split("; ");
    const tokenItem = list.find((item) => item.includes(`${DM_TOKEN_COOKIE_KEY}=`));
    if (tokenItem) {
        const val = tokenItem.replace(`${DM_TOKEN_COOKIE_KEY}=`, "");
        if (val) {
            return val.split("_")[0];
        }
    }

    return "";
}

export function commonTip(message) {
    if (message.includes(MSG_TOKEN_EXPIRED)) {
        Message.warning("Cookie 已过期，请重新填写");
    } else if (message.includes("invalid signature") || message.includes("签名错误")) {
        Message.error(
            "签名验证失败——可能是大麦更新了 appKey，请检查 src/utils/dm/dm-config.js 中的 DM_APP_KEY"
        );
    } else if (message.includes("FAIL_BIZ_NOT_OPEN")) {
        Message.warning(
            "接口版本可能已变更，请检查 src-tauri/src/dm_config.rs 中的 API_VERSION_* 常量"
        );
    }
}

export function isSuccess(message) {
    return message.includes("SUCCESS");
}

export function joinMsg(list) {
    if (Array.isArray(list)) {
        return list.join("; ");
    }

    return list;
}

export function combinationOrderParams(data, selectUserList) {
    const res = {
        params: {
            // data: {},
            // linkage: {},
            // hierarchy: {},
        },
        feature: {
            subChannel: DM_SUB_CHANNEL,
            returnUrl:
                "https://m.damai.cn/damai/pay-success/index.html?spm=a2o71.orderconfirm.bottom.dconfirm&sqm=dianying.h5.unknown.value",
            serviceVersion: "2.0.0",
            dataTags: "sqm:dianying.h5.unknown.value",
        },
    };

    // params - data
    const tagList = ORDER_TAG_LIST;

    let localData = {};
    for (const [key, value] of Object.entries(data.data)) {
        if (tagList.includes(value.tag)) {
            if (value.tag === "dmViewer") {
                let formatValue = value;
                // 说明需要选择观演人
                if (Array.isArray(formatValue.fields.viewerList)) {
                    formatValue.fields.selectedNum =
                        formatValue.fields.viewerList.length;
                    formatValue.fields.viewerList =
                        formatValue.fields.viewerList.map((item) => {
                            let current = {
                                ...item,
                                isDisabled: false,
                            };
                            current.isUsed = selectUserList.includes(
                                item.maskedIdentityNo
                            );

                            return current;
                        });
                }
                localData[key] = formatValue;
            } else {
                localData[key] = value;
            }
        }
    }
    // to json
    res.params.data = cusJSON(localData);

    // params - linkage
    let linkage = {
        common: {
            compress: Boolean(data.linkage.common.compress),
            submitParams: data.linkage.common.submitParams,
            validateParams: data.linkage.common.validateParams,
        },
        signature: data.linkage.signature,
    };
    res.params.linkage = cusJSON(linkage);

    let hierarchy = {
        structure: {},
    };
    // params - hierarchy
    const hierarchyList = ORDER_HIERARCHY_LIST;
    hierarchyList.forEach((key) => {
        for (let parentKey in res.params.hierarchy) {
            if (parentKey.startsWith(key)) {
                hierarchy.structure[parentKey] =
                    data.hierarchy.structure[parentKey];
            }
        }
    });
    res.params.hierarchy = cusJSON(hierarchy);

    // to json
    res.params = JSON.stringify(res.params);

    // to json
    res.feature = JSON.stringify(res.feature);

    return res;
}

export function cusJSON(e) {
    var t = [];
    t.push({
        obj: e,
    });
    for (var n, r, o, i, a, u, c, s, l, f, d = ""; (n = t.pop()); )
        if (((r = n.obj), (d += n.prefix || ""), (o = n.val || ""))) d += o;
        else if ("object" != typeof r)
            d += void 0 === r ? null : JSON.stringify(r);
        else if (null === r) d += "null";
        else if (Array.isArray(r)) {
            for (
                t.push({
                    val: "]",
                }),
                    i = r.length - 1;
                i >= 0;
                i--
            )
                (a = 0 === i ? "" : ","),
                    t.push({
                        obj: r[i],
                        prefix: a,
                    });
            t.push({
                val: "[",
            });
        } else {
            for (c in ((u = []), r)) r.hasOwnProperty(c) && u.push(c);
            for (
                t.push({
                    val: "}",
                }),
                    i = u.length - 1;
                i >= 0;
                i--
            )
                (l = r[(s = u[i])]),
                    (f = i > 0 ? "," : ""),
                    (f += JSON.stringify(s) + ":"),
                    t.push({
                        obj: l,
                        prefix: f,
                    });
            t.push({
                val: "{",
            });
        }
    return d;
}

export function encode(e) {
    var t = [];
    for (var n in e) {
        e[n] && t.push(n + "=" + encodeURIComponent(e[n]));
    }
    return t.join("&");
}

// 判断文案（从配置统一导出，保持向后兼容）
export { MSG_HAVE_ORDER as HAVE_ORDER, MSG_VALIDATE as VALIDATE } from "./dm-config.js";
