function navigateTo(sel, target, newWindow) {
    var url = sel.options[sel.selectedIndex].value;
    if (newWindow) {
        window.open(url, target, 'toolbar=1');
    } else {
        window[target].location.href = url;
    }
}
