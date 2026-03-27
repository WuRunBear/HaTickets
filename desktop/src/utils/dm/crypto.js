export function getSign(data, token) {
    var u = "12574478",
        s = new Date().getTime(),
        c = (function (t) {
            function e(t, e) {
                return (t << e) | (t >>> (32 - e));
            }
            function n(t, e) {
                var n, r, o, i, a;
                return (
                    (o = 2147483648 & t),
                    (i = 2147483648 & e),
                    (a = (1073741823 & t) + (1073741823 & e)),
                    (n = 1073741824 & t) & (r = 1073741824 & e)
                        ? 2147483648 ^ a ^ o ^ i
                        : n | r
                        ? 1073741824 & a
                            ? 3221225472 ^ a ^ o ^ i
                            : 1073741824 ^ a ^ o ^ i
                        : a ^ o ^ i
                );
            }
            function r(t, r, o, i, a, u, s) {
                return (
                    (t = n(
                        t,
                        n(
                            n(
                                (function (t, e, n) {
                                    return (t & e) | (~t & n);
                                })(r, o, i),
                                a
                            ),
                            s
                        )
                    )),
                    n(e(t, u), r)
                );
            }
            function o(t, r, o, i, a, u, s) {
                return (
                    (t = n(
                        t,
                        n(
                            n(
                                (function (t, e, n) {
                                    return (t & n) | (e & ~n);
                                })(r, o, i),
                                a
                            ),
                            s
                        )
                    )),
                    n(e(t, u), r)
                );
            }
            function i(t, r, o, i, a, u, s) {
                return (
                    (t = n(
                        t,
                        n(
                            n(
                                (function (t, e, n) {
                                    return t ^ e ^ n;
                                })(r, o, i),
                                a
                            ),
                            s
                        )
                    )),
                    n(e(t, u), r)
                );
            }
            function a(t, r, o, i, a, u, s) {
                return (
                    (t = n(
                        t,
                        n(
                            n(
                                (function (t, e, n) {
                                    return e ^ (t | ~n);
                                })(r, o, i),
                                a
                            ),
                            s
                        )
                    )),
                    n(e(t, u), r)
                );
            }
            function u(t) {
                var e,
                    n = "",
                    r = "";
                for (e = 0; 3 >= e; e++)
                    n += (r =
                        "0" + ((t >>> (8 * e)) & 255).toString(16)).substr(
                        r.length - 2,
                        2
                    );
                return n;
            }
            var s, c, f, l, p, d, h, v, m, g;
            for (
                g = (function (t) {
                    for (
                        var e,
                            n = t.length,
                            r = n + 8,
                            o = 16 * ((r - (r % 64)) / 64 + 1),
                            i = new Array(o - 1),
                            a = 0,
                            u = 0;
                        n > u;

                    )
                        (a = (u % 4) * 8),
                            (i[(e = (u - (u % 4)) / 4)] =
                                i[e] | (t.charCodeAt(u) << a)),
                            u++;
                    return (
                        (a = (u % 4) * 8),
                        (i[(e = (u - (u % 4)) / 4)] = i[e] | (128 << a)),
                        (i[o - 2] = n << 3),
                        (i[o - 1] = n >>> 29),
                        i
                    );
                })(
                    (t = (function (t) {
                        t = t.replace(/\r\n/g, "\n");
                        for (var e = "", n = 0; n < t.length; n++) {
                            var r = t.charCodeAt(n);
                            128 > r
                                ? (e += String.fromCharCode(r))
                                : r > 127 && 2048 > r
                                ? ((e += String.fromCharCode((r >> 6) | 192)),
                                  (e += String.fromCharCode((63 & r) | 128)))
                                : ((e += String.fromCharCode((r >> 12) | 224)),
                                  (e += String.fromCharCode(
                                      ((r >> 6) & 63) | 128
                                  )),
                                  (e += String.fromCharCode((63 & r) | 128)));
                        }
                        return e;
                    })(t))
                ),
                    d = 1732584193,
                    h = 4023233417,
                    v = 2562383102,
                    m = 271733878,
                    s = 0;
                s < g.length;
                s += 16
            )
                (c = d),
                    (f = h),
                    (l = v),
                    (p = m),
                    (d = r(d, h, v, m, g[s + 0], 7, 3614090360)),
                    (m = r(m, d, h, v, g[s + 1], 12, 3905402710)),
                    (v = r(v, m, d, h, g[s + 2], 17, 606105819)),
                    (h = r(h, v, m, d, g[s + 3], 22, 3250441966)),
                    (d = r(d, h, v, m, g[s + 4], 7, 4118548399)),
                    (m = r(m, d, h, v, g[s + 5], 12, 1200080426)),
                    (v = r(v, m, d, h, g[s + 6], 17, 2821735955)),
                    (h = r(h, v, m, d, g[s + 7], 22, 4249261313)),
                    (d = r(d, h, v, m, g[s + 8], 7, 1770035416)),
                    (m = r(m, d, h, v, g[s + 9], 12, 2336552879)),
                    (v = r(v, m, d, h, g[s + 10], 17, 4294925233)),
                    (h = r(h, v, m, d, g[s + 11], 22, 2304563134)),
                    (d = r(d, h, v, m, g[s + 12], 7, 1804603682)),
                    (m = r(m, d, h, v, g[s + 13], 12, 4254626195)),
                    (v = r(v, m, d, h, g[s + 14], 17, 2792965006)),
                    (d = o(
                        d,
                        (h = r(h, v, m, d, g[s + 15], 22, 1236535329)),
                        v,
                        m,
                        g[s + 1],
                        5,
                        4129170786
                    )),
                    (m = o(m, d, h, v, g[s + 6], 9, 3225465664)),
                    (v = o(v, m, d, h, g[s + 11], 14, 643717713)),
                    (h = o(h, v, m, d, g[s + 0], 20, 3921069994)),
                    (d = o(d, h, v, m, g[s + 5], 5, 3593408605)),
                    (m = o(m, d, h, v, g[s + 10], 9, 38016083)),
                    (v = o(v, m, d, h, g[s + 15], 14, 3634488961)),
                    (h = o(h, v, m, d, g[s + 4], 20, 3889429448)),
                    (d = o(d, h, v, m, g[s + 9], 5, 568446438)),
                    (m = o(m, d, h, v, g[s + 14], 9, 3275163606)),
                    (v = o(v, m, d, h, g[s + 3], 14, 4107603335)),
                    (h = o(h, v, m, d, g[s + 8], 20, 1163531501)),
                    (d = o(d, h, v, m, g[s + 13], 5, 2850285829)),
                    (m = o(m, d, h, v, g[s + 2], 9, 4243563512)),
                    (v = o(v, m, d, h, g[s + 7], 14, 1735328473)),
                    (d = i(
                        d,
                        (h = o(h, v, m, d, g[s + 12], 20, 2368359562)),
                        v,
                        m,
                        g[s + 5],
                        4,
                        4294588738
                    )),
                    (m = i(m, d, h, v, g[s + 8], 11, 2272392833)),
                    (v = i(v, m, d, h, g[s + 11], 16, 1839030562)),
                    (h = i(h, v, m, d, g[s + 14], 23, 4259657740)),
                    (d = i(d, h, v, m, g[s + 1], 4, 2763975236)),
                    (m = i(m, d, h, v, g[s + 4], 11, 1272893353)),
                    (v = i(v, m, d, h, g[s + 7], 16, 4139469664)),
                    (h = i(h, v, m, d, g[s + 10], 23, 3200236656)),
                    (d = i(d, h, v, m, g[s + 13], 4, 681279174)),
                    (m = i(m, d, h, v, g[s + 0], 11, 3936430074)),
                    (v = i(v, m, d, h, g[s + 3], 16, 3572445317)),
                    (h = i(h, v, m, d, g[s + 6], 23, 76029189)),
                    (d = i(d, h, v, m, g[s + 9], 4, 3654602809)),
                    (m = i(m, d, h, v, g[s + 12], 11, 3873151461)),
                    (v = i(v, m, d, h, g[s + 15], 16, 530742520)),
                    (d = a(
                        d,
                        (h = i(h, v, m, d, g[s + 2], 23, 3299628645)),
                        v,
                        m,
                        g[s + 0],
                        6,
                        4096336452
                    )),
                    (m = a(m, d, h, v, g[s + 7], 10, 1126891415)),
                    (v = a(v, m, d, h, g[s + 14], 15, 2878612391)),
                    (h = a(h, v, m, d, g[s + 5], 21, 4237533241)),
                    (d = a(d, h, v, m, g[s + 12], 6, 1700485571)),
                    (m = a(m, d, h, v, g[s + 3], 10, 2399980690)),
                    (v = a(v, m, d, h, g[s + 10], 15, 4293915773)),
                    (h = a(h, v, m, d, g[s + 1], 21, 2240044497)),
                    (d = a(d, h, v, m, g[s + 8], 6, 1873313359)),
                    (m = a(m, d, h, v, g[s + 15], 10, 4264355552)),
                    (v = a(v, m, d, h, g[s + 6], 15, 2734768916)),
                    (h = a(h, v, m, d, g[s + 13], 21, 1309151649)),
                    (d = a(d, h, v, m, g[s + 4], 6, 4149444226)),
                    (m = a(m, d, h, v, g[s + 11], 10, 3174756917)),
                    (v = a(v, m, d, h, g[s + 2], 15, 718787259)),
                    (h = a(h, v, m, d, g[s + 9], 21, 3951481745)),
                    (d = n(d, c)),
                    (h = n(h, f)),
                    (v = n(v, l)),
                    (m = n(m, p));
            return (u(d) + u(h) + u(v) + u(m)).toLowerCase();
        })(token + "&" + s + "&" + u + "&" + data);

    return [s, c];
}
