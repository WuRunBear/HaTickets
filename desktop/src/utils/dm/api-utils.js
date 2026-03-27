import { Message } from "@arco-design/web-vue";

export function getToken(cookie) {
    const list = cookie.split("; ");
    const tokenItem = list.find((item) => item.includes("_m_h5_tk="));
    if (tokenItem) {
        const val = tokenItem.replace("_m_h5_tk=", "");
        if (val) {
            return val.split("_")[0];
        }
    }

    return "";
}

export function commonTip(message) {
    if (message.includes("令牌过期")) {
        Message.warning("cookie过期，请重新填写");
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
            subChannel: "damai@damaih5_h5",
            returnUrl:
                "https://m.damai.cn/damai/pay-success/index.html?spm=a2o71.orderconfirm.bottom.dconfirm&sqm=dianying.h5.unknown.value",
            serviceVersion: "2.0.0",
            dataTags: "sqm:dianying.h5.unknown.value",
        },
    };

    // params - data
    const tagList = [
        "dmPayType",
        "dmEttributesHiddenBlock",
        "dmContactEmail",
        "dmViewer",
        "dmDeliverySelectCard",
        "dmContactPhone",
        "confirmOrder",
        "dmDeliveryAddress",
        "dmContactName",
        "item",
    ];

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
    let hierarchyList = [
        "dmPayDetailPopupWindowBlock_",
        "dmViewerBlock_DmViewerBlock",
        "dmContactBlock_DmContactBlock",
        "dmItemBlock_DmItemBlock",
        "dmDeliveryWayBlock_DmDeliveryWayBlock",
        "deliveryMethodOptions_",
        "confirmOrder_1",
        "dmOrderSubmitBlock_DmOrderSubmitBlock",
        "order_",
        "dmPayTypeBlock_DmPayTypeBlock",
        "dmTopNotificationBlock_DmTopNotificationBlock",
    ];
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

// 判断文案
export const HAVE_ORDER = "您还有未支付订单";
export const VALIDATE = "FAIL_SYS_USER_VALIDATE";
