const EasyCoder_Paypal = {

	name: `EasyCoder_Paypal`,

	Paypal: {

		// Command keywords
		compile: compiler => {
			const lino = compiler.getLino();
			compiler.next();
			compiler.addCommand({
				domain: `paypal`,
				keyword: `paypal`,
				lino
			});
			return true;
		},

		run: program => {
			const command = program[program.pc];
            console.log(`This is Paypal`);
			return command.pc + 1;
		}
	},

	// Values
	value: {

		compile: () => {
			return {
				domain: `paypal`,
				type: `paypal`
			};
		},

		get: (program, value) => {
			return value;
		}
	},

	// Conditions
	condition: {

		compile: () => {},

		test: () => {}
	},

	// Dispatcher
	getHandler: (name) => {
		switch (name) {
		case `paypal`:
			return EasyCoder_Paypal.Paypal;
		default:
			return false;
		}
	},

	run: program => {
		const command = program[program.pc];
		const handler = EasyCoder_Paypal.getHandler(command.keyword);
		if (!handler) {
			program.runtimeError(command.lino, `Unknown keyword '${command.keyword}' in 'paypal' package`);
		}
		return handler.run(program);
	}
};

// eslint-disable-next-line no-unused-vars
EasyCoder.domain.paypal = EasyCoder_Paypal;
