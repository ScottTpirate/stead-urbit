import { rename, rm } from 'node:fs/promises';
// The caller owns the uniquely named staging directory and holds its build lock.
// Optional operations allow filesystem failure tests without runtime bypass flags.
export async function publishDirectory(staging, destination, operations = {rename, rm}) {
  const previous = staging + '-previous';
  let movedPrevious = false;
  try { await operations.rename(destination, previous); movedPrevious = true; }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  try { await operations.rename(staging, destination); }
  catch (error) {
    if (movedPrevious) {
      try { await operations.rename(previous, destination); }
      catch (rollback) { throw new AggregateError([error, rollback], `Build publication and rollback failed; preserved output: ${previous}`); }
    }
    throw error;
  }
  if (movedPrevious) await operations.rm(previous, {recursive: true});
}
