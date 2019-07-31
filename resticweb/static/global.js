
// string formatter found on StackOverflow
// https://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format
String.prototype.formatUnicorn = String.prototype.formatUnicorn ||
function () {
    "use strict";
    var str = this.toString();
    if (arguments.length) {
        var t = typeof arguments[0];
        var key;
        var args = ("string" === t || "number" === t) ?
            Array.prototype.slice.call(arguments)
            : arguments[0];

        for (key in args) {
            str = str.replace(new RegExp("\\{" + key + "\\}", "gi"), args[key]);
        }
    }

    return str;
};

function getVisibleItemIds() {
    var itemList = $( ".list-checkbox" ).get();
    var idList = [];
    for (var i = 0; i < itemList.length; i++) {
        idList.push(parseInt(itemList[i].value, 10));
    }
    return idList;
}