<script setup lang="js">
import { ref, reactive, onMounted } from "vue";
import {
    loadBaxiaScript,
    initBaxia,
    loadBaxiaTime,
} from "../utils/dm/index.js";
import { Message } from "@arco-design/web-vue";
import Form from '../components/dm/Form.vue'
import Product from '../components/dm/Product.vue'

onMounted(() => {
    // 加载凭证脚本
    loadBaxiaScript();
    // 初始化凭证
    setTimeout(() => {
        let res = initBaxia();
        if (!res) {
            Message.error(
                "凭证脚本初始化失败，抢票功能无法使用。可能原因：\n" +
                "1. 网络无法访问阿里 CDN，请检查网络\n" +
                "2. Baxia SDK 版本已变更，请更新 src/utils/dm/dm-config.js 中的 BAXIA_VERSIONED_URL\n" +
                "排查后请重新启动程序。"
            );
        }
    }, loadBaxiaTime);
});


// 商品组件引用
const productRef = ref(null)

// 获取商品信息
const handleSubmit = async () => {
    // await getProductInfo();
    // if(productInfo.value) {
        formActive.value = []
    // }
    productRef.value.getProductInfo()
};

// 展示收起逻辑
const formActive = ref(['1'])
function collapseChange() {
    if(formActive.value.length) {
        formActive.value = []
    } else {
        formActive.value = ['1']
    }
}
</script>

<template>
    <div class="container">
        <a-collapse :activeKey="formActive" :onChange="collapseChange">
            <a-collapse-item header="基本信息" key="1">
                <Form :handleSubmit="handleSubmit"></Form>
            </a-collapse-item>
        </a-collapse>
        <product ref="productRef"></product>
    </div>
</template>

<style scoped lang="scss"></style>
