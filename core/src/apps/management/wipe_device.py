import storage
from trezor.messages.Success import Success
from trezor.ui.layouts import confirm_wipe, require


async def wipe_device(ctx, msg):
    await require(confirm_wipe(ctx))

    storage.wipe()

    return Success(message="Device wiped")
