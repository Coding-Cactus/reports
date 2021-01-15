function disable_resolve() {
	const buttons = document.querySelectorAll("button");
	buttons.forEach(function(button) {
		button.disabled = true;
	});
}

const buttons = document.querySelectorAll("button");
	buttons.forEach(function(button) {
		button.addEventListener('click', () => {
			button.parentNode.submit();
			disable_resolve();
			});
	});