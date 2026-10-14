// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors

#include "emu.h"
#include "cpu/m68000/m68000.h"

namespace {

class alphasdana_state : public driver_device
{
public:
	alphasdana_state(const machine_config &mconfig, device_type type, const char *tag)
		: driver_device(mconfig, type, tag)
		, m_maincpu(*this, "maincpu")
	{
	}

	void alphasdana(machine_config &config);

private:
	required_device<m68000_device> m_maincpu;
};

void alphasdana_state::alphasdana(machine_config &config)
{
	// Registration-only placeholder; this clock is not a Dana timing model.
	M68000(config, m_maincpu, 1'000'000);
}

static INPUT_PORTS_START(alphasdana)
INPUT_PORTS_END

ROM_START(asmdana)
ROM_END

} // anonymous namespace

COMP(2002, asmdana, 0, 0, alphasdana, alphasdana, alphasdana_state, empty_init,
	"AlphaSmart, Inc.", "AlphaSmart Dana (D1.1 skeleton)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND)
