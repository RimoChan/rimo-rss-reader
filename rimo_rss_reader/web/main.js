const http = (url, data, f) => {
    let httpRequest = new XMLHttpRequest();
    httpRequest.open('POST', url, true);
    httpRequest.send(JSON.stringify(data));
    httpRequest.onreadystatechange = () => {
        if (httpRequest.readyState == 4 && httpRequest.status == 200) {
            var json = httpRequest.responseText;
            if (f)
                f(JSON.parse(json));
        }
    };
}

const 单次加载个数 = 100

const app = Vue.createApp({
    data() {
        return {
            所有订阅组: {},
            当前订阅组: null,
            喂: {},
            没有了: {},
            小窗: '',
            假read: {},
        }
    },
    methods: {
        吃(x) {
            this.当前订阅组 = x
            this.刷新()
        },
        加载喂(多个订阅组, 最多数量, 开始时间) {
            for (const 订阅组 of 多个订阅组)
                if (!this.喂[订阅组])
                    this.喂[订阅组] = {}
            http('超喂', { 源: 多个订阅组, 最多数量, 开始时间 }, (x) => {
                for (const 订阅组 in x) {
                    const n = Object.keys(this.喂[订阅组]).length
                    for (const i of x[订阅组])
                        this.喂[订阅组][i.id] = i
                    if (x[订阅组].length < 最多数量) {
                        this.没有了[订阅组] = true
                    }
                    console.log(`【${订阅组}】原有 ${n} 个entry，新获取 ${Object.keys(x).length} 个entry，现在有 ${Object.keys(this.喂[订阅组]).length} 个entry。`)
                }
            })
        },
        刷新() {
            this.加载喂([this.当前订阅组], 单次加载个数)
        },
        加载更多() {
            o = this.查看当前订阅组()
            最后时间 = o[o.length - 1]['_entry_time']
            this.加载喂([this.当前订阅组], 单次加载个数, 最后时间)
        },
        查看当前订阅组() {
            o = this.喂[this.当前订阅组]
            if (!o)
                return []
            return Object.values(o).sort((a, b) => b['_entry_time'] - a['_entry_time'])
        },
        标为已读(item) {
            this.假read[item.id] = true
            console.log(this.假read)
            http('标为已读', { feed_url: item._feed_url, entry_time: item._entry_time, id: item.id })
        },
        全部标为已读() {
            Object.values(this.喂[this.当前订阅组]).forEach((x) => this.假read[x.id] = true)
            for (const i of this.所有订阅组[this.当前订阅组]) {
                http('全部标为已读', { feed_url: i.url })
            }
        },
        全部展开(b) {
            for (const i of document.querySelectorAll("details"))
                i.open = b
        },
        format_time(date) {
            let d = new Date(date)
            return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()} ${d.getHours()}:${d.getMinutes()}`
        }
    },
    mounted() {
        http('所有订阅组', {}, (x) => {
            this.所有订阅组 = x
            this.当前订阅组 = Object.keys(x)[0]
            this.加载喂(Object.keys(this.所有订阅组), 10)
            this.加载喂(Object.keys(this.所有订阅组), 单次加载个数)
            setInterval(() => {
                http('所有订阅组', {}, (x) => {
                    this.所有订阅组 = x
                })
                this.加载喂(Object.keys(this.所有订阅组), 单次加载个数)
            }, 1000 * 10)
        })
    }
})
window.onload = () => app.mount('#app')
