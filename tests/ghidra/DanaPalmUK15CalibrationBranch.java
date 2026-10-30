// @category Dana
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Instruction;
import java.io.PrintWriter;
import java.io.FileWriter;
public class DanaPalmUK15CalibrationBranch extends GhidraScript {
  public void run() throws Exception {
    PrintWriter f=new PrintWriter(new FileWriter(getScriptArgs()[0]));
    for(long[] range : new long[][]{
      {0x1007F59AL,0x1007F842L},
      {0x1007B64CL,0x1007B7A0L},
      {0x1007F880L,0x1007FA80L}
    }) {
      f.printf("BEGIN %08X..%08X\n",range[0],range[1]);
      for(long pc=range[0];pc<range[1];){
        Instruction ins=getInstructionAt(toAddr(pc));
        if(ins==null){try{disassemble(toAddr(pc));}catch(Exception ignored){}ins=getInstructionAt(toAddr(pc));}
        if(ins==null){pc+=2;continue;}
        f.printf("%08X %-18s %s\n",pc,ins.getMnemonicString(),ins.toString());
        pc+=ins.getLength();
      }
    }
    f.close();
    println("CALIBRATION_GHIDRA_DONE");
  }
}
